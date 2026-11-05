"""
Pruebas del registro de aprendices (registro por número de grupo,
datos personales nuevos y validaciones del servidor).

Se ejecutan con:   python manage.py test usuarios
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from usuarios.forms import RegistroAprendizForm
from usuarios.models import Aprendiz, Grupo, Jornada, NivelFormacion, ProgramaFormacion, Usuario


class RegistroBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.diurna = Jornada.objects.create(nombre="Diurna")
        cls.nocturna = Jornada.objects.create(nombre="Nocturna")
        cls.mixta = Jornada.objects.create(nombre="Mixta")  # sin grupos

        # La migración 0007 ya deja creados "Técnico" y "Tecnólogo".
        cls.tecnologo, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        cls.tecnico, _ = NivelFormacion.objects.get_or_create(nombre="Técnico")

        cls.prog_ads = ProgramaFormacion.objects.create(
            nombre="Análisis y Desarrollo de Software", codigo="228118",
            nivel_formacion=cls.tecnologo, duracion_meses=24,
        )
        cls.prog_tec = ProgramaFormacion.objects.create(
            nombre="Técnico en Sistemas", codigo="111111",
            nivel_formacion=cls.tecnico, duracion_meses=12,
        )
        cls.prog_inactivo = ProgramaFormacion.objects.create(
            nombre="Programa Antiguo", codigo="999999",
            nivel_formacion=cls.tecnico, duracion_meses=12, estado="inactivo",
        )

        def grupo(numero, programa, jornada, estado="activa"):
            return Grupo.objects.create(
                numero_grupo=numero, programa_formacion=programa, jornada=jornada,
                fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 12, 31), estado=estado,
            )

        cls.g_ads_dia = grupo("3171693", cls.prog_ads, cls.diurna)
        cls.g_ads_noc = grupo("3171694", cls.prog_ads, cls.nocturna)
        cls.g_ads_cerrado = grupo("3000000", cls.prog_ads, cls.mixta, estado="cerrada")
        cls.g_tec_dia = grupo("2999999", cls.prog_tec, cls.diurna)
        # Terminó hace tiempo pero nadie lo cerró a mano: igual deja de ofrecerse.
        cls.g_ads_terminado = Grupo.objects.create(
            numero_grupo="2000001", programa_formacion=cls.prog_ads, jornada=cls.diurna,
            fecha_inicio=date(2020, 1, 1), fecha_fin=date(2021, 12, 31), estado="activa")

    def datos_validos(self, **cambios):
        datos = {
            "nombres": "Juan",
            "apellidos": "Rodríguez",
            "tipo_documento": "CC",
            "numero_documento": "1012345678",
            "genero": "M",
            "email": "juan@example.com",
            "telefono": "300 123 4567",
            "numero_grupo": self.g_ads_dia.numero_grupo,
            "password": "ClaveSegura#2026",
            "password_confirm": "ClaveSegura#2026",
        }
        datos.update(cambios)
        return datos


class EndpointsGrupoTests(RegistroBase):

    def consultar(self, numero):
        return self.client.get(reverse("usuarios:grupo_por_numero"), {"numero": numero}).json()

    def test_numero_valido_devuelve_programa_jornada_y_nivel(self):
        d = self.consultar("3171693")
        self.assertTrue(d["encontrado"])
        self.assertEqual((d["programa"], d["jornada"], d["nivel"]),
                         ("Análisis y Desarrollo de Software", "Diurna", "Tecnólogo"))

    def test_ignora_espacios(self):
        self.assertTrue(self.consultar(" 317 1693 ")["encontrado"])

    def test_numero_inexistente_o_vacio(self):
        for malo in ("9999999", "", "   ", "1 OR 1=1"):
            d = self.consultar(malo)
            self.assertFalse(d["encontrado"], malo)
            self.assertTrue(d["mensaje"])

    def test_grupo_cerrado_o_terminado_no_se_ofrece(self):
        self.assertFalse(self.consultar("3000000")["encontrado"])     # cerrado a mano
        self.assertFalse(self.consultar("2000001")["encontrado"])     # terminó por fecha
        self.assertIn("terminó", self.consultar("2000001")["mensaje"])

    def test_programa_inactivo_no_se_ofrece(self):
        Grupo.objects.create(numero_grupo="1111111", programa_formacion=self.prog_inactivo,
                             jornada=self.diurna, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 12, 31))
        self.assertFalse(self.consultar("1111111")["encontrado"])

    def test_grupos_por_programa_solo_vigentes(self):
        r = self.client.get(reverse("usuarios:grupos_por_programa"), {"programa_formacion": self.prog_ads.id})
        self.assertEqual(sorted(f["numero_grupo"] for f in r.json()), ["3171693", "3171694"])
        r = self.client.get(reverse("usuarios:grupos_por_programa"),
                            {"programa_formacion": self.prog_ads.id, "jornada": self.nocturna.id})
        self.assertEqual([f["numero_grupo"] for f in r.json()], ["3171694"])

    def test_grupos_parametro_invalido(self):
        r = self.client.get(reverse("usuarios:grupos_por_programa"), {"programa_formacion": "1 OR 1=1"})
        self.assertEqual(r.json(), [])


class RegistroTests(RegistroBase):

    def test_get_muestra_los_tres_pasos(self):
        r = self.client.get(reverse("usuarios:registro"))
        self.assertEqual(r.status_code, 200)
        for texto in ("Datos personales", "Tu grupo", "Crea tu contraseña",
                      "Género", "Teléfono de contacto", "Número de grupo"):
            self.assertContains(r, texto)

    def test_registro_valido_guarda_todo_y_hace_login(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos())
        self.assertRedirects(r, reverse("usuarios:dashboard"), fetch_redirect_response=False)

        u = Usuario.objects.get(numero_documento="1012345678")
        self.assertEqual(u.genero, "M")
        self.assertEqual(u.telefono, "3001234567")  # sin espacios
        self.assertEqual(u.aprendiz.grupo, self.g_ads_dia)
        self.assertEqual(self.client.session["_auth_user_id"], str(u.pk))

    def test_el_grupo_define_programa_jornada_y_nivel(self):
        self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo="3171694"))
        g = Usuario.objects.get(numero_documento="1012345678").aprendiz.grupo
        self.assertEqual((g.programa_formacion, g.jornada), (self.prog_ads, self.nocturna))

    def test_numero_de_grupo_inexistente_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo="9999999"))
        self.assertIn("numero_grupo", r.context["form"].errors)
        self.assertEqual(Aprendiz.objects.count(), 0)

    def test_grupo_cerrado_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo="3000000"))
        self.assertEqual(Aprendiz.objects.count(), 0)
        self.assertIn("numero_grupo", r.context["form"].errors)

    def test_grupo_que_ya_termino_por_fecha_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo="2000001"))
        self.assertEqual(Aprendiz.objects.count(), 0)
        self.assertContains(r, "ya terminó")

    def test_el_numero_se_acepta_con_espacios(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo=" 317 1693 "))
        self.assertRedirects(r, reverse("usuarios:dashboard"), fetch_redirect_response=False)

    def test_programa_inactivo_es_rechazado(self):
        Grupo.objects.create(numero_grupo="1111111", programa_formacion=self.prog_inactivo,
                             jornada=self.diurna, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 12, 31))
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo="1111111"))
        self.assertIn("numero_grupo", r.context["form"].errors)

    def test_campos_nuevos_son_obligatorios(self):
        for campo in ("genero", "telefono", "numero_grupo"):
            r = self.client.post(reverse("usuarios:registro"), self.datos_validos(**{campo: ""}))
            self.assertIn(campo, r.context["form"].errors, campo)

    def test_genero_solo_masculino_o_femenino(self):
        for valido in ("M", "F"):
            self.assertTrue(RegistroAprendizForm(self.datos_validos(genero=valido)).is_valid(), valido)
        for invalido in ("O", "N", "X"):
            form = RegistroAprendizForm(self.datos_validos(genero=invalido))
            self.assertFalse(form.is_valid(), invalido)
            self.assertIn("genero", form.errors, invalido)

    def test_telefono_invalido(self):
        for malo in ("abc", "123", "30012345678901234"):
            form = RegistroAprendizForm(self.datos_validos(telefono=malo))
            self.assertFalse(form.is_valid(), malo)
            self.assertIn("telefono", form.errors, malo)

    def test_telefono_se_normaliza(self):
        for entrada, esperado in (("300-123-4567", "3001234567"), ("+57 300 123 4567", "+573001234567")):
            form = RegistroAprendizForm(self.datos_validos(telefono=entrada))
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data["telefono"], esperado)

    def test_documento_y_correo_duplicados(self):
        self.client.post(reverse("usuarios:registro"), self.datos_validos())
        self.client.logout()
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(email="JUAN@example.com"))
        self.assertIn("numero_documento", r.context["form"].errors)
        self.assertIn("email", r.context["form"].errors)

    def test_contrasenas_distintas_abren_el_paso_3(self):
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(password_confirm="otra"))
        self.assertEqual(r.context["form"].paso_con_errores(), 3)
        self.assertContains(r, 'data-paso-inicial="3"')

    def test_error_en_grupo_abre_el_paso_2_y_conserva_el_numero(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(numero_grupo="9999999"))
        self.assertEqual(r.context["form"].paso_con_errores(), 2)
        self.assertContains(r, 'value="9999999"')

    def test_error_en_datos_personales_abre_el_paso_1(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(email="no-es-correo"))
        self.assertEqual(r.context["form"].paso_con_errores(), 1)

    def test_sin_grupos_vigentes_avisa_en_pantalla(self):
        Grupo.objects.update(estado="cerrada")
        r = self.client.get(reverse("usuarios:registro"))
        self.assertContains(r, "Todavía no hay grupos vigentes")

    def test_usuario_autenticado_es_redirigido(self):
        self.client.post(reverse("usuarios:registro"), self.datos_validos())
        r = self.client.get(reverse("usuarios:registro"))
        self.assertEqual(r.status_code, 302)
