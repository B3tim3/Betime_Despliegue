"""
Grupos vigentes vs. historial: el registro y los paneles solo trabajan con lo vigente, y los
grupos que terminan se van solos al historial (sin que nadie los cierre a mano).
"""

from datetime import date, timedelta
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Grupo, Jornada, NivelFormacion, PersonalBienestar, ProgramaFormacion, Usuario


class GruposVigentesBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        hoy = timezone.localdate()
        cls.hoy = hoy
        jornada = Jornada.objects.create(nombre="Diurna")
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        cls.programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="1", nivel_formacion=nivel, duracion_meses=24)

        def grupo(numero, fin, estado="activa", inicio=None):
            return Grupo.objects.create(
                numero_grupo=numero, programa_formacion=cls.programa, jornada=jornada,
                fecha_inicio=inicio or fin - timedelta(days=300), fecha_fin=fin, estado=estado)

        cls.vigente = grupo("1000001", hoy + timedelta(days=200))
        cls.futuro = grupo("1000002", hoy + timedelta(days=700), inicio=hoy + timedelta(days=100))
        cls.termina_hoy = grupo("1000003", hoy)                       # el día de fin aún cuenta
        cls.finalizado = grupo("1000004", hoy - timedelta(days=1))     # terminó por fecha
        cls.finalizado_2020 = grupo("1000005", date(2020, 6, 1))
        cls.cerrado = grupo("1000006", hoy + timedelta(days=200), estado="cerrada")

        cls.staff = Usuario.objects.create_user(
            numero_documento="900000010", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Paola", apellidos="Bienestar", email="paola@example.com")
        PersonalBienestar.objects.create(usuario=cls.staff, cargo="P", fecha_ingreso=date(2026, 1, 1))

    def setUp(self):
        self.client.force_login(self.staff)

    def numeros(self, respuesta):
        return [g.numero_grupo for g in respuesta.context["grupos"]]


class ModeloTests(GruposVigentesBase):

    def test_vigentes_e_historial_son_complementarios(self):
        vig = set(Grupo.objects.vigentes().values_list("numero_grupo", flat=True))
        his = set(Grupo.objects.historial().values_list("numero_grupo", flat=True))
        self.assertEqual(vig, {"1000001", "1000002", "1000003"})
        self.assertEqual(his, {"1000004", "1000005", "1000006"})
        self.assertFalse(vig & his)

    def test_vigencia_de_cada_grupo(self):
        self.assertEqual(self.vigente.vigencia, "vigente")
        self.assertEqual(self.termina_hoy.vigencia, "vigente")
        self.assertEqual(self.finalizado.vigencia, "finalizado")
        self.assertEqual(self.cerrado.vigencia, "cerrado")
        self.assertEqual(self.finalizado.vigencia_etiqueta, "Finalizado")

    def test_con_vigencia(self):
        self.assertEqual(list(Grupo.objects.con_vigencia("cerrado")), [self.cerrado])
        self.assertEqual(Grupo.objects.con_vigencia("finalizado").count(), 2)


class PanelGruposTests(GruposVigentesBase):

    def test_por_defecto_solo_vigentes(self):
        r = self.client.get(reverse("usuarios:grupos_lista"))
        self.assertEqual(sorted(self.numeros(r)), ["1000001", "1000002", "1000003"])
        self.assertEqual(r.context["total_vigentes"], 3)
        self.assertEqual(r.context["total_historial"], 3)

    def test_historial_trae_finalizados_y_cerrados(self):
        r = self.client.get(reverse("usuarios:grupos_lista"), {"vista": "historial"})
        self.assertEqual(sorted(self.numeros(r)), ["1000004", "1000005", "1000006"])
        self.assertContains(r, "Finalizado")
        self.assertContains(r, "Cerrado")

    def test_filtro_por_anio_y_estado_en_el_historial(self):
        url = reverse("usuarios:grupos_lista")
        r = self.client.get(url, {"vista": "historial", "anio": "2020"})
        self.assertEqual(self.numeros(r), ["1000005"])
        r = self.client.get(url, {"vista": "historial", "estado": "cerrado"})
        self.assertEqual(self.numeros(r), ["1000006"])
        self.assertIn(2020, r.context["anios"])

    def test_buscar_por_numero_en_el_servidor(self):
        r = self.client.get(reverse("usuarios:grupos_lista"), {"vista": "historial", "q": "1000005"})
        self.assertEqual(self.numeros(r), ["1000005"])
        r = self.client.get(reverse("usuarios:grupos_lista"), {"q": "ADSO"})
        self.assertEqual(len(self.numeros(r)), 3)

    def test_la_paginacion_conserva_pestana_y_busqueda(self):
        for i in range(20):
            Grupo.objects.create(
                numero_grupo=f"77{i:05d}", programa_formacion=self.programa, jornada=self.vigente.jornada,
                fecha_inicio=date(2015, 1, 1), fecha_fin=date(2016, 1, 1))
        r = self.client.get(reverse("usuarios:grupos_lista"), {"vista": "historial", "q": "77"})
        self.assertTrue(r.context["is_paginated"])
        self.assertContains(r, "page=2&amp;vista=historial&amp;q=77")

    def test_exportar_trae_lo_mismo_que_la_pantalla(self):
        from openpyxl import load_workbook
        r = self.client.get(reverse("usuarios:grupos_exportar"), {"formato": "excel", "vista": "historial", "anio": "2020"})
        self.assertEqual(r.status_code, 200)
        filas = [[c.value for c in f] for f in load_workbook(BytesIO(r.content)).active.iter_rows()]
        numeros = [f[0] for f in filas if f and f[0] and str(f[0]).startswith("10000")]
        self.assertEqual(numeros, ["1000005"])
        estados = [f[-1] for f in filas if f and f[0] == "1000005"]
        self.assertEqual(estados, ["Finalizado"])

    def test_el_enlace_de_exportar_lleva_los_filtros(self):
        r = self.client.get(reverse("usuarios:grupos_lista"), {"vista": "historial", "q": "10"})
        self.assertContains(r, "vista=historial")


class FormulariosDePanelTests(GruposVigentesBase):

    def test_editar_aprendiz_ofrece_vigentes_y_el_grupo_actual_aunque_haya_terminado(self):
        from usuarios.forms.aprendiz_panel import AprendizPanelForm
        from usuarios.models import Aprendiz
        u = Usuario.objects.create_user(
            numero_documento="1012345678", password="x", tipo_documento="CC",
            nombres="J", apellidos="R", email="j@x.co")
        ap = Aprendiz.objects.create(usuario=u, grupo=self.finalizado, fecha_ingreso=date(2026, 1, 1))
        ids = set(AprendizPanelForm(instance=ap).fields["grupo"].queryset.values_list("numero_grupo", flat=True))
        self.assertEqual(ids, {"1000001", "1000002", "1000003", "1000004"})   # +el suyo, sin el resto
