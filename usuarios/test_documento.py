"""Validación del número de documento (registro, crear usuario, corregir aprendiz)."""

from datetime import date
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from usuarios.forms import LoginForm
from usuarios.models import Usuario
from usuarios.test_registro import RegistroBase
from usuarios.validators import documento_es_valido, validar_numero_documento


class ValidadorTests(SimpleTestCase):

    def test_cedula_tarjeta_y_extranjeria_solo_digitos(self):
        for tipo in ("CC", "TI", "CE"):
            self.assertEqual(validar_numero_documento(tipo, " 1012345678 "), "1012345678")
            for malo in ("dylanquintero1025@gmail.com", "10123abc", "1012 345", "1.012.345", "10-123456",
                         "١٢٣٤٥٦٧", "１２３４５６７", "12.345", "abc", "ñandú12345"):
                with self.assertRaises(ValidationError, msg=f"{tipo} {malo!r}"):
                    validar_numero_documento(tipo, malo)

    def test_largo_numerico(self):
        validar_numero_documento("CC", "12345")               # 5: mínimo
        validar_numero_documento("CC", "123456789012")        # 12: máximo
        for malo in ("1234", "1234567890123", ""):
            with self.assertRaises(ValidationError):
                validar_numero_documento("CC", malo)

    def test_pep_y_ppt_aceptan_letras_y_numeros_en_mayusculas(self):
        self.assertEqual(validar_numero_documento("PEP", "abc12345"), "ABC12345")
        self.assertEqual(validar_numero_documento("PPT", "123456789012345"), "123456789012345")
        for tipo in ("PEP", "PPT"):
            for malo in ("ab c123", "abc-123", "abc@123", "a" * 21, "abcd"):
                with self.assertRaises(ValidationError, msg=f"{tipo} {malo!r}"):
                    validar_numero_documento(tipo, malo)

    def test_sin_tipo_solo_limpia(self):
        self.assertEqual(validar_numero_documento(None, " x "), "x")

    def test_documento_es_valido(self):
        self.assertTrue(documento_es_valido("CC", "1012345678"))
        self.assertFalse(documento_es_valido("CC", "a@b.co"))


class RegistroDocumentoTests(RegistroBase):

    def test_el_registro_rechaza_un_correo_como_documento(self):
        r = self.client.post("/usuarios/registro/", self.datos_validos(numero_documento="dylan1025@gmail.com"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(numero_documento__contains="@").exists())
        self.assertContains(r, "solo puede tener números")

    def test_el_registro_rechaza_letras_con_cedula(self):
        from usuarios.forms import RegistroAprendizForm
        form = RegistroAprendizForm(self.datos_validos(numero_documento="1012ABC678"))
        self.assertFalse(form.is_valid())
        self.assertIn("numero_documento", form.errors)

    def test_el_registro_acepta_pep_con_letras_y_lo_guarda_en_mayusculas(self):
        from usuarios.forms import RegistroAprendizForm
        form = RegistroAprendizForm(self.datos_validos(tipo_documento="PEP", numero_documento="ab12345cd"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["numero_documento"], "AB12345CD")

    def test_cambiar_el_tipo_cambia_la_regla(self):
        from usuarios.forms import RegistroAprendizForm
        self.assertFalse(RegistroAprendizForm(self.datos_validos(tipo_documento="CC", numero_documento="AB12345")).is_valid())
        self.assertTrue(RegistroAprendizForm(self.datos_validos(tipo_documento="PPT", numero_documento="AB12345")).is_valid())


class CrearUsuarioYEdicionTests(TestCase):

    def test_crear_usuario_admin_valida_el_documento(self):
        from usuarios.forms import CrearUsuarioAdminForm
        base = {"tipo_perfil": "administrador", "tipo_documento": "CC", "nombres": "A", "apellidos": "B",
                "email": "ad@x.co", "cargo": "Coordinador", "password": "ClaveSegura#2026",
                "password_confirm": "ClaveSegura#2026"}
        malo = CrearUsuarioAdminForm({**base, "numero_documento": "admin@x.co"})
        self.assertFalse(malo.is_valid())
        self.assertIn("numero_documento", malo.errors)
        bueno = CrearUsuarioAdminForm({**base, "numero_documento": "1098765432"})
        self.assertNotIn("numero_documento", bueno.errors)

    def test_login_no_se_bloquea_con_cuentas_antiguas_invalidas(self):
        """La validación es para registrar/editar: quien ya tiene una cuenta rara sigue pudiendo entrar."""
        Usuario.objects.create_user(numero_documento="viejo@x.co", password="x", tipo_documento="TI",
                                    nombres="V", apellidos="J", email="v@x.co")
        form = LoginForm({"tipo_documento": "TI", "numero_documento": "viejo@x.co", "password": "x"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_comando_lista_las_cuentas_invalidas_sin_modificarlas(self):
        Usuario.objects.create_user(numero_documento="viejo@x.co", password="x", tipo_documento="TI",
                                    nombres="V", apellidos="J", email="v@x.co")
        Usuario.objects.create_user(numero_documento="1012345678", password="x", tipo_documento="CC",
                                    nombres="B", apellidos="C", email="b@x.co")
        salida = StringIO()
        call_command("revisar_documentos", stdout=salida)
        texto = salida.getvalue()
        self.assertIn("viejo@x.co", texto)
        self.assertNotIn("1012345678", texto)
        self.assertEqual(Usuario.objects.count(), 2)
