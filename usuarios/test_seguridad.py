"""
Pruebas de seguridad (Paquete Seguridad 1): bloqueo por intentos fallidos
de login, cierre de sesión solo por POST, cierre por inactividad y mensaje
de login que no revela si un documento existe.

Se ejecutan con:   python manage.py test usuarios.test_seguridad
"""

import time
from datetime import date, timedelta

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from usuarios.middleware import CLAVE_ACTIVIDAD, CierreSesionPorInactividadMiddleware
from usuarios.models import (
    Aprendiz, Grupo, IntentoFallido, Jornada, NivelFormacion, PersonalBienestar,
    ProgramaFormacion, Usuario,
)
from usuarios.services.bloqueo import MAX_INTENTOS, VENTANA_MINUTOS, minutos_de_bloqueo

CLAVE = "Clave-Segura-1"
MENSAJE_INCORRECTO = "Documento o contraseña incorrectos."

# Los tests de inactividad activan el middleware por su cuenta, así pasan
# aunque settings.py todavía no lo tenga en MIDDLEWARE.
MW = "usuarios.middleware.CierreSesionPorInactividadMiddleware"
MIDDLEWARE_CON_INACTIVIDAD = [m for m in settings.MIDDLEWARE if m != MW] + [MW]


class Base(TestCase):

    @classmethod
    def setUpTestData(cls):
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        jor = Jornada.objects.create(nombre="Diurna")
        prog = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
        grupo = Grupo.objects.create(
            numero_grupo="3000001", programa_formacion=prog, jornada=jor,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))
        u = Usuario.objects.create_user(
            numero_documento="101", password=CLAVE, tipo_documento="CC",
            nombres="Ana", apellidos="Pérez", email="a@x.co")
        Aprendiz.objects.create(usuario=u, grupo=grupo, fecha_ingreso=date(2026, 1, 1))
        s = Usuario.objects.create_user(
            numero_documento="900", password=CLAVE, tipo_documento="CC",
            nombres="Paola", apellidos="Ramírez", email="p@x.co")
        PersonalBienestar.objects.create(usuario=s, cargo="C", fecha_ingreso=date(2026, 1, 1))

    def intentar(self, documento="101", clave="mala", tipo="CC"):
        return self.client.post(reverse("usuarios:login"), {
            "tipo_documento": tipo, "numero_documento": documento, "password": clave,
        }, follow=True)

    def textos(self, respuesta):
        return [str(m) for m in respuesta.context["messages"]]


class BloqueoLoginTests(Base):

    def test_cinco_fallos_bloquean_aunque_luego_la_clave_sea_correcta(self):
        for _ in range(MAX_INTENTOS):
            r = self.intentar()
            self.assertIn(MENSAJE_INCORRECTO, self.textos(r))

        r = self.intentar(clave=CLAVE)  # la correcta, pero ya está bloqueado
        self.assertTrue(any("Demasiados intentos" in t for t in self.textos(r)))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_un_intento_menos_no_bloquea(self):
        for _ in range(MAX_INTENTOS - 1):
            self.intentar()
        r = self.intentar(clave=CLAVE)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(r.redirect_chain[-1][0], reverse("usuarios:dashboard_aprendiz"))

    def test_login_correcto_borra_los_fallos(self):
        for _ in range(MAX_INTENTOS - 1):
            self.intentar()
        self.intentar(clave=CLAVE)
        self.assertFalse(IntentoFallido.objects.filter(numero_documento="101").exists())

    def test_el_bloqueo_es_por_documento(self):
        for _ in range(MAX_INTENTOS):
            self.intentar("101")
        self.assertGreater(minutos_de_bloqueo("101"), 0)
        self.assertEqual(minutos_de_bloqueo("900"), 0)
        self.intentar("900", CLAVE)
        self.assertIn("_auth_user_id", self.client.session)

    def test_documento_inexistente_se_comporta_igual(self):
        for _ in range(MAX_INTENTOS):
            r = self.intentar("999999")
            self.assertIn(MENSAJE_INCORRECTO, self.textos(r))
        r = self.intentar("999999")
        self.assertTrue(any("Demasiados intentos" in t for t in self.textos(r)))

    def test_el_bloqueo_termina_con_el_tiempo(self):
        for _ in range(MAX_INTENTOS):
            self.intentar()
        IntentoFallido.objects.update(fecha=timezone.now() - timedelta(minutes=VENTANA_MINUTOS + 1))
        self.assertEqual(minutos_de_bloqueo("101"), 0)
        self.intentar(clave=CLAVE)
        self.assertIn("_auth_user_id", self.client.session)

    def test_intentos_bloqueados_no_alargan_el_castigo(self):
        for _ in range(MAX_INTENTOS):
            self.intentar()
        antes = IntentoFallido.objects.count()
        for _ in range(3):
            self.intentar()
        self.assertEqual(IntentoFallido.objects.count(), antes)

    def test_minutos_restantes_se_redondean_hacia_arriba(self):
        for _ in range(MAX_INTENTOS):
            self.intentar()
        espera = minutos_de_bloqueo("101")
        self.assertTrue(1 <= espera <= VENTANA_MINUTOS)
        r = self.intentar()
        self.assertTrue(any(f"espera {espera} minuto" in t for t in self.textos(r)))

    def test_tipo_de_documento_equivocado_no_revela_que_el_documento_existe(self):
        r = self.intentar("101", CLAVE, tipo="TI")  # 101 existe pero como CC
        self.assertContains(r, MENSAJE_INCORRECTO)
        self.assertNotContains(r, "no coincide")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(IntentoFallido.objects.filter(numero_documento="101").count(), 1)

    def test_limpieza_de_intentos_viejos(self):
        IntentoFallido.objects.create(numero_documento="555")
        IntentoFallido.objects.update(fecha=timezone.now() - timedelta(days=3))
        self.intentar("101")  # un fallo nuevo dispara la limpieza
        self.assertFalse(IntentoFallido.objects.filter(numero_documento="555").exists())

    def test_documento_vacio_o_enorme_no_rompe(self):
        r = self.intentar("", "x")
        self.assertEqual(r.status_code, 200)
        r = self.intentar("9" * 500, "x")
        self.assertEqual(r.status_code, 200)

    def test_acceso_personal_tambien_se_bloquea(self):
        for _ in range(MAX_INTENTOS):
            self.client.post(reverse("usuarios:login_personal"), {
                "tipo_documento": "CC", "numero_documento": "900", "password": "mala"})
        r = self.client.post(reverse("usuarios:login_personal"), {
            "tipo_documento": "CC", "numero_documento": "900", "password": CLAVE}, follow=True)
        self.assertTrue(any("Demasiados intentos" in t for t in self.textos(r)))


class LogoutTests(Base):

    def test_get_no_cierra_sesion(self):
        self.client.login(numero_documento="101", password=CLAVE)
        r = self.client.get(reverse("usuarios:logout"))
        self.assertEqual(r.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_cierra_sesion(self):
        self.client.login(numero_documento="101", password=CLAVE)
        r = self.client.post(reverse("usuarios:logout"))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_la_barra_usa_un_formulario_post(self):
        self.client.login(numero_documento="101", password=CLAVE)
        for url in (reverse("usuarios:dashboard_aprendiz"), "/"):
            r = self.client.get(url)
            html = r.content.decode()
            self.assertIn(f'method="post" action="{reverse("usuarios:logout")}"', html)
            self.assertNotIn(f'href="{reverse("usuarios:logout")}"', html)


@override_settings(MIDDLEWARE=MIDDLEWARE_CON_INACTIVIDAD)
class InactividadTests(Base):

    def envejecer(self, segundos):
        sesion = self.client.session
        sesion[CLAVE_ACTIVIDAD] = int(time.time()) - segundos
        sesion.save()

    def test_aprendiz_activo_sigue_con_sesion(self):
        self.client.login(numero_documento="101", password=CLAVE)
        self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.envejecer(10 * 60)
        r = self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertEqual(r.status_code, 200)

    def test_aprendiz_inactivo_se_desloguea_con_aviso(self):
        self.client.login(numero_documento="101", password=CLAVE)
        self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.envejecer(31 * 60)
        r = self.client.get(reverse("usuarios:dashboard_aprendiz"), follow=True)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(any("inactividad" in t for t in self.textos(r)))

    def test_personal_tiene_mas_tiempo_que_el_aprendiz(self):
        self.client.login(numero_documento="900", password=CLAVE)
        self.client.get(reverse("usuarios:dashboard_bienestar"))
        self.envejecer(60 * 60)   # 1 h: al aprendiz ya lo habría sacado
        r = self.client.get(reverse("usuarios:dashboard_bienestar"))
        self.assertEqual(r.status_code, 200)
        self.envejecer(2 * 60 * 60 + 60)
        self.client.get(reverse("usuarios:dashboard_bienestar"))
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(INACTIVIDAD_SEGUNDOS=120)
    def test_el_tiempo_se_puede_configurar(self):
        self.client.login(numero_documento="101", password=CLAVE)
        self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.envejecer(3 * 60)
        self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_la_marca_no_se_reescribe_en_cada_clic(self):
        self.client.login(numero_documento="101", password=CLAVE)
        self.client.get(reverse("usuarios:dashboard_aprendiz"))
        primera = self.client.session[CLAVE_ACTIVIDAD]
        self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertEqual(self.client.session[CLAVE_ACTIVIDAD], primera)

    def test_solo_la_primera_peticion_escribe_la_sesion(self):
        """Después de la 1.ª petición, las siguientes (dentro del minuto) no tocan la sesión en la base de datos."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.login(numero_documento="101", password=CLAVE)
        url = reverse("usuarios:dashboard_aprendiz")
        self.client.get(url)                       # 1.ª: crea las marcas (y la configuración)
        consultas = []
        for _ in range(3):
            with CaptureQueriesContext(connection) as c:
                self.client.get(url)
            consultas.append(len(c))
        self.assertEqual(len(set(consultas)), 1, consultas)
        self.assertFalse(any("UPDATE \"django_session\"" in q["sql"] for q in c.captured_queries))

    def test_visitante_sin_sesion_no_se_ve_afectado(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
