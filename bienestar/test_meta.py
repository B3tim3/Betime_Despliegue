"""
Pruebas de la meta de horas de bienestar (configurable por el administrador)
y de la barra de progreso del panel del aprendiz.

Se ejecutan con:   python manage.py test bienestar.test_meta
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bienestar.models import ConfiguracionBienestar, HorasBienestar
from bienestar.services import registrar_asistencia_y_horas
from bienestar.services.progreso import calcular_progreso
from eventos.models import Evento, Inscripcion
from usuarios.models import (
    Administrador, Grupo, Jornada, NivelFormacion, PersonalBienestar, ProgramaFormacion, Usuario,
)
from usuarios.services import registrar_aprendiz


class ConfiguracionModeloTests(TestCase):

    def test_por_defecto_son_40_horas(self):
        self.assertEqual(ConfiguracionBienestar.obtener().meta_horas, 40)

    def test_siempre_es_un_unico_registro(self):
        ConfiguracionBienestar.obtener()
        ConfiguracionBienestar(meta_horas=50).save()
        ConfiguracionBienestar(meta_horas=60).save()
        self.assertEqual(ConfiguracionBienestar.objects.count(), 1)
        self.assertEqual(ConfiguracionBienestar.obtener().meta_horas, 60)


class CalculoProgresoTests(TestCase):

    def test_progreso_parcial(self):
        p = calcular_progreso(10, meta=40)
        self.assertEqual((p["total"], p["meta"], p["porcentaje"], p["faltantes"], p["completo"]),
                         (10, 40, 25, 30, False))

    def test_meta_cumplida_y_superada_no_pasa_de_100(self):
        self.assertTrue(calcular_progreso(40, meta=40)["completo"])
        p = calcular_progreso(55, meta=40)
        self.assertEqual((p["porcentaje"], p["faltantes"], p["completo"]), (100, 0, True))

    def test_sin_horas(self):
        p = calcular_progreso(0, meta=40)
        self.assertEqual((p["porcentaje"], p["faltantes"]), (0, 40))
        self.assertEqual(calcular_progreso(None, meta=40)["total"], 0)

    def test_usa_la_meta_configurada(self):
        ConfiguracionBienestar(meta_horas=20).save()
        self.assertEqual(calcular_progreso(10)["porcentaje"], 50)


class VistasBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        jornada = Jornada.objects.create(nombre="Diurna")
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="228118", nivel_formacion=nivel, duracion_meses=24)
        grupo = Grupo.objects.create(
            numero_grupo="3171693", programa_formacion=programa, jornada=jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 12, 31))

        cls.usuario, cls.aprendiz = registrar_aprendiz(
            tipo_documento="CC", numero_documento="1012345678", nombres="Juan",
            apellidos="Rodríguez", email="juan@example.com", password="ClaveSegura#2026",
            grupo=grupo, genero="M", telefono="3001234567")

        cls.admin = Usuario.objects.create_user(
            numero_documento="900000001", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Admin", apellidos="Be Time", email="admin@example.com")
        Administrador.objects.create(usuario=cls.admin, fecha_ingreso=date(2026, 1, 1))

        cls.bienestar_user = Usuario.objects.create_user(
            numero_documento="900000002", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Paola", apellidos="Bienestar", email="paola@example.com")
        cls.personal = PersonalBienestar.objects.create(
            usuario=cls.bienestar_user, cargo="Profesional", fecha_ingreso=date(2026, 1, 1))

        cls.evento = Evento.objects.create(
            titulo="Taller", descripcion="x", lugar="Aula",
            fecha_inicio=timezone.now(), fecha_fin=timezone.now() + timezone.timedelta(hours=2),
            horas_otorgadas=10, creado_por=cls.bienestar_user)
        cls.inscripcion = Inscripcion.objects.create(evento=cls.evento, aprendiz=cls.aprendiz)


class ConfiguracionVistaTests(VistasBase):

    def setUp(self):
        self.url = reverse("bienestar:configuracion")

    def test_el_admin_cambia_la_meta(self):
        self.client.force_login(self.admin)
        r = self.client.post(self.url, {"meta_horas": 60})
        self.assertRedirects(r, self.url, fetch_redirect_response=False)
        self.assertEqual(ConfiguracionBienestar.obtener().meta_horas, 60)

    def test_valores_invalidos(self):
        self.client.force_login(self.admin)
        for malo in ("0", "-5", "abc", "5000", ""):
            r = self.client.post(self.url, {"meta_horas": malo})
            self.assertEqual(r.status_code, 200, malo)
            self.assertIn("meta_horas", r.context["form"].errors, malo)
        self.assertEqual(ConfiguracionBienestar.obtener().meta_horas, 40)

    def test_bienestar_no_puede_cambiarla(self):
        self.client.force_login(self.bienestar_user)
        r = self.client.post(self.url, {"meta_horas": 99})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ConfiguracionBienestar.obtener().meta_horas, 40)

    def test_aprendiz_no_puede_cambiarla(self):
        self.client.force_login(self.usuario)
        self.client.post(self.url, {"meta_horas": 99})
        self.assertEqual(ConfiguracionBienestar.obtener().meta_horas, 40)

    def test_sin_sesion_va_al_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)

    def test_enlace_solo_para_el_admin(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("usuarios:dashboard_admin")), self.url)
        self.client.force_login(self.bienestar_user)
        self.assertNotContains(self.client.get(reverse("usuarios:dashboard_bienestar")), self.url)


class BarraDeProgresoTests(VistasBase):

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = reverse("usuarios:dashboard_aprendiz")

    def test_sin_horas(self):
        r = self.client.get(self.url)
        self.assertContains(r, "de 40 horas")
        self.assertContains(r, "te faltan 40 horas")
        self.assertEqual(r.context["progreso"]["porcentaje"], 0)

    def test_con_horas(self):
        registrar_asistencia_y_horas(
            inscripcion=self.inscripcion, asistio=True, cantidad_horas=10,
            motivo="x", asignado_por=self.personal)
        r = self.client.get(self.url)
        self.assertContains(r, "25% completado")
        self.assertContains(r, "te faltan 30 horas")

    def test_la_meta_cambiada_se_refleja(self):
        ConfiguracionBienestar(meta_horas=20).save()
        registrar_asistencia_y_horas(
            inscripcion=self.inscripcion, asistio=True, cantidad_horas=10,
            motivo="x", asignado_por=self.personal)
        r = self.client.get(self.url)
        self.assertContains(r, "de 20 horas")
        self.assertContains(r, "50% completado")

    def test_meta_cumplida(self):
        ConfiguracionBienestar(meta_horas=10).save()
        registrar_asistencia_y_horas(
            inscripcion=self.inscripcion, asistio=True, cantidad_horas=10,
            motivo="x", asignado_por=self.personal)
        r = self.client.get(self.url)
        self.assertContains(r, "Completaste tus horas de bienestar")
        self.assertEqual(r.context["progreso"]["porcentaje"], 100)
