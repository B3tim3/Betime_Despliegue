from django.core import mail
import os
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Usuario


class CorreoRecuperacionTests(TestCase):

    def test_correo_con_html_logo_y_texto(self):
        Usuario.objects.create_user(
            numero_documento="1234567", password="x", tipo_documento="CC",
            nombres="Ana María", apellidos="Gómez", email="ana@x.co")
        self.client.post(reverse("usuarios:password_reset"), {"email": "ana@x.co"})
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.subject, "Recupera tu contraseña de Be Time")
        self.assertIn("Ana María", m.body)
        self.assertIn("/recuperar-contrasena/confirmar/", m.body)
        self.assertNotIn("1234567", m.body)            # el documento va oculto
        html = m.alternatives[0][0]
        self.assertIn("Crear nueva contraseña", html)
        self.assertIn("cid:logo-betime", html)
        self.assertIn("••••567", html)
        self.assertNotIn("1234567", html)
        self.assertIn("3 días", html)      # vigencia por defecto de Django
        # el logo viaja adjunto, embebido
        mime = m.message().as_string()
        self.assertIn("Content-ID: <logo-betime>", mime)
        self.assertIn("multipart/related", mime)
        self.assertIn("image/png", mime)


class EnlaceYVigenciaTests(TestCase):

    def setUp(self):
        Usuario.objects.create_user(
            numero_documento="1234567", password="x", tipo_documento="CC",
            nombres="Ana", apellidos="Gómez", email="ana@x.co")

    def _pedir(self, **extra):
        self.client.post(reverse("usuarios:password_reset"), {"email": "ana@x.co"}, **extra)
        return mail.outbox[-1]

    @override_settings(PASSWORD_RESET_TIMEOUT=20 * 60)
    def test_vigencia_de_20_minutos(self):
        m = self._pedir()
        self.assertIn("20 minutos", m.body)
        self.assertIn("20 minutos", m.alternatives[0][0])

    @override_settings(PASSWORD_RESET_TIMEOUT=20 * 60)
    def test_el_enlace_expira(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils import timezone
        from datetime import timedelta
        usuario = Usuario.objects.get(numero_documento="1234567")
        token = default_token_generator.make_token(usuario)
        self.assertTrue(default_token_generator.check_token(usuario, token))
        futuro = timezone.now() + timedelta(minutes=21)
        with mock.patch.object(default_token_generator, "_now", return_value=futuro.replace(tzinfo=None)):
            self.assertFalse(default_token_generator.check_token(usuario, token))

    def test_enlace_usa_site_url_con_tunel(self):
        with mock.patch.dict(os.environ, {"SITE_URL": "https://abc-def.trycloudflare.com/"}):
            m = self._pedir()
        self.assertIn("https://abc-def.trycloudflare.com/usuarios/recuperar-contrasena/confirmar/", m.body)
        self.assertNotIn("localhost", m.body)
        self.assertNotIn("testserver", m.body)

    def test_sin_site_url_usa_la_peticion_y_https_del_proxy(self):
        with mock.patch.dict(os.environ, {"SITE_URL": ""}):
            m = self._pedir(HTTP_X_FORWARDED_PROTO="https")
        self.assertIn("https://testserver/usuarios/recuperar-contrasena/confirmar/", m.body)

    def test_una_cabecera_falsa_no_cambia_el_enlace(self):
        with mock.patch.dict(os.environ, {"SITE_URL": ""}):
            m = self._pedir(HTTP_ORIGIN="https://malo.example", HTTP_REFERER="https://malo.example/x")
        self.assertNotIn("malo.example", m.body)
