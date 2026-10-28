"""
Estado automático de los eventos: programado / en curso / finalizado salen
de las fechas; "cancelado" es el único manual y nunca se pisa.
"""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from eventos.models import Evento
from eventos.services.estados import sincronizar_estados
from eventos.services.inscripciones import InscripcionError, inscribir
from usuarios.models import (
    Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar,
    ProgramaFormacion, Usuario,
)

CLAVE = "Clave-Segura-1"


class EstadosAutomaticosTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        jornada = Jornada.objects.create(nombre="Diurna")
        programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
        grupo = Grupo.objects.create(
            numero_grupo="3000001", programa_formacion=programa, jornada=jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))

        def usuario(doc, nombre):
            return Usuario.objects.create_user(
                numero_documento=doc, password=CLAVE, tipo_documento="CC",
                nombres=nombre, apellidos="Prueba", email=f"{doc}@x.co")

        cls.u_personal = usuario("2", "Personal")
        PersonalBienestar.objects.create(usuario=cls.u_personal, cargo="C", fecha_ingreso=date(2026, 1, 1))
        cls.u_ap = usuario("3", "Aprendiz")
        cls.aprendiz = Aprendiz.objects.create(usuario=cls.u_ap, grupo=grupo, fecha_ingreso=date(2026, 1, 1))

    def evento(self, desde, hasta, **extra):
        ahora = timezone.now()
        return Evento.objects.create(
            titulo="Yoga", lugar="Coliseo", horas_otorgadas=2, creado_por=self.u_personal,
            fecha_inicio=ahora + desde, fecha_fin=ahora + hasta, **extra)

    # ---------- al guardar ----------

    def test_se_calcula_al_crear(self):
        self.assertEqual(self.evento(timedelta(days=1), timedelta(days=1, hours=2)).estado, "programado")
        self.assertEqual(self.evento(-timedelta(hours=1), timedelta(hours=1)).estado, "en_curso")
        self.assertEqual(self.evento(-timedelta(days=1), -timedelta(hours=22)).estado, "finalizado")

    def test_ignora_el_estado_que_se_le_pase(self):
        # Aunque alguien diga "finalizado", un evento futuro es programado.
        self.assertEqual(self.evento(timedelta(days=1), timedelta(days=2), estado="finalizado").estado, "programado")

    def test_cancelado_no_se_pisa(self):
        ev = self.evento(-timedelta(days=2), -timedelta(days=1), estado="cancelado")
        self.assertEqual(ev.estado, "cancelado")
        ev.save()
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "cancelado")
        self.assertEqual(ev.estado_actual, "cancelado")

    def test_editar_las_fechas_cambia_el_estado(self):
        ev = self.evento(timedelta(days=1), timedelta(days=1, hours=2))
        ev.fecha_inicio = timezone.now() - timedelta(hours=1)
        ev.fecha_fin = timezone.now() + timedelta(hours=1)
        ev.save()
        self.assertEqual(ev.estado, "en_curso")

    # ---------- el paso del tiempo ----------

    def test_sincronizar_avanza_con_el_reloj(self):
        ev = self.evento(timedelta(hours=1), timedelta(hours=3))
        self.assertEqual(ev.estado, "programado")
        sincronizar_estados(timezone.now() + timedelta(hours=2))
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "en_curso")
        sincronizar_estados(timezone.now() + timedelta(hours=4))
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "finalizado")

    def test_sincronizar_no_toca_cancelados_ni_cambia_lo_correcto(self):
        cancelado = self.evento(-timedelta(days=2), -timedelta(days=1), estado="cancelado")
        bien = self.evento(timedelta(days=1), timedelta(days=2))
        self.assertEqual(sincronizar_estados(), 0)
        cancelado.refresh_from_db(); bien.refresh_from_db()
        self.assertEqual((cancelado.estado, bien.estado), ("cancelado", "programado"))

    def test_datos_viejos_desactualizados_se_corrigen(self):
        ev = self.evento(-timedelta(days=2), -timedelta(days=1))
        Evento.objects.filter(pk=ev.pk).update(estado="programado")   # como quedó antes de esta mejora
        self.assertEqual(sincronizar_estados(), 1)
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "finalizado")

    def test_no_se_puede_inscribir_aunque_la_base_este_desactualizada(self):
        ev = self.evento(-timedelta(hours=1), timedelta(hours=1))
        Evento.objects.filter(pk=ev.pk).update(estado="programado")   # obsoleto
        ev.refresh_from_db()
        with self.assertRaises(InscripcionError):
            inscribir(self.aprendiz, ev)

    # ---------- pantallas ----------

    def test_las_vistas_ponen_al_dia_el_estado(self):
        ev = self.evento(-timedelta(days=2), -timedelta(days=1))
        Evento.objects.filter(pk=ev.pk).update(estado="programado")
        self.client.force_login(self.u_personal)
        r = self.client.get(reverse("eventos:panel_lista"))
        self.assertContains(r, "Finalizado")
        self.assertEqual(Evento.objects.get(pk=ev.pk).estado, "finalizado")

    def test_la_lista_publica_incluye_en_curso_y_oculta_cancelados_y_finalizados(self):
        en_curso = self.evento(-timedelta(hours=1), timedelta(hours=1))
        self.evento(-timedelta(days=2), -timedelta(days=1))
        self.evento(timedelta(days=1), timedelta(days=2), estado="cancelado")
        r = self.client.get(reverse("eventos:lista"))
        self.assertEqual([e.pk for e in r.context["eventos"]], [en_curso.pk])

    # ---------- formulario ----------

    def datos_form(self, **extra):
        ini = timezone.now() + timedelta(days=2)
        datos = {
            "titulo": "Yoga", "descripcion": "", "lugar": "Coliseo", "horas_otorgadas": 2,
            "fecha_inicio": timezone.localtime(ini).strftime("%Y-%m-%d %H:%M"),
            "fecha_fin": timezone.localtime(ini + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
        }
        datos.update(extra)
        return datos

    def test_formulario_cancelar_y_volver_a_automatico(self):
        self.client.force_login(self.u_personal)
        ev = self.evento(timedelta(days=2), timedelta(days=2, hours=2))
        url = reverse("eventos:editar", args=[ev.pk])
        self.client.post(url, self.datos_form(estado="cancelado"))
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "cancelado")
        # "Automático" lo reactiva y el estado vuelve a salir de las fechas
        self.client.post(url, self.datos_form(estado=""))
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "programado")

    def test_formulario_acepta_valores_viejos_como_automatico(self):
        self.client.force_login(self.u_personal)
        ev = self.evento(timedelta(days=2), timedelta(days=2, hours=2))
        self.client.post(reverse("eventos:editar", args=[ev.pk]), self.datos_form(estado="finalizado"))
        ev.refresh_from_db()
        self.assertEqual(ev.estado, "programado")   # un evento futuro nunca es "finalizado"
