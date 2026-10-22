"""
Pruebas del registro de aprendices (cascada programa -> jornada -> grupo,
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

    def datos_validos(self, **cambios):
        datos = {
            "nombres": "Juan",
            "apellidos": "Rodríguez",
            "tipo_documento": "CC",
            "numero_documento": "1012345678",
            "genero": "M",
            "email": "juan@example.com",
            "telefono": "300 123 4567",
            "programa_formacion": self.prog_ads.id,
            "jornada": self.diurna.id,
            "grupo": self.g_ads_dia.id,
            "password": "ClaveSegura#2026",
            "password_confirm": "ClaveSegura#2026",
        }
        datos.update(cambios)
        return datos


class EndpointsCascadaTests(RegistroBase):

    def test_jornadas_solo_las_que_tienen_grupos_activos(self):
        r = self.client.get(reverse("usuarios:jornadas_por_programa"),
                            {"programa_formacion": self.prog_ads.id})
        datos = r.json()
        nombres = [j["nombre"] for j in datos["jornadas"]]
        self.assertEqual(sorted(nombres), ["Diurna", "Nocturna"])  # Mixta solo tiene un grupo cerrado
        self.assertEqual(datos["nivel"], "Tecnólogo")

    def test_jornadas_programa_inactivo_o_invalido_devuelve_vacio(self):
        url = reverse("usuarios:jornadas_por_programa")
        for valor in (self.prog_inactivo.id, "abc", "", "99999"):
            r = self.client.get(url, {"programa_formacion": valor})
            self.assertEqual(r.json(), {"nivel": "", "jornadas": []}, valor)

    def test_grupos_filtrados_por_jornada(self):
        r = self.client.get(reverse("usuarios:grupos_por_programa"),
                            {"programa_formacion": self.prog_ads.id, "jornada": self.nocturna.id})
        self.assertEqual([f["numero_grupo"] for f in r.json()], ["3171694"])

    def test_grupos_sin_jornada_sigue_funcionando_como_antes(self):
        # Compatibilidad: el formulario de crear usuario del panel solo filtra por programa.
        r = self.client.get(reverse("usuarios:grupos_por_programa"),
                            {"programa_formacion": self.prog_ads.id})
        self.assertEqual(sorted(f["numero_grupo"] for f in r.json()), ["3171693", "3171694"])

    def test_grupos_parametro_invalido(self):
        r = self.client.get(reverse("usuarios:grupos_por_programa"),
                            {"programa_formacion": "1 OR 1=1"})
        self.assertEqual(r.json(), [])


class RegistroTests(RegistroBase):

    def test_get_muestra_los_tres_pasos(self):
        r = self.client.get(reverse("usuarios:registro"))
        self.assertEqual(r.status_code, 200)
        for texto in ("Datos personales", "Programa de formación", "Crea tu contraseña",
                      "Género", "Teléfono de contacto", "Número de grupo", "Nivel de formación"):
            self.assertContains(r, texto)

    def test_registro_valido_guarda_todo_y_hace_login(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos())
        self.assertRedirects(r, reverse("usuarios:dashboard"), fetch_redirect_response=False)

        u = Usuario.objects.get(numero_documento="1012345678")
        self.assertEqual(u.genero, "M")
        self.assertEqual(u.telefono, "3001234567")  # sin espacios
        self.assertEqual(u.aprendiz.grupo, self.g_ads_dia)
        self.assertEqual(self.client.session["_auth_user_id"], str(u.pk))

    def test_grupo_de_otro_programa_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(grupo=self.g_tec_dia.id))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(numero_documento="1012345678").exists())
        self.assertIn("grupo", r.context["form"].errors)

    def test_grupo_de_otra_jornada_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(grupo=self.g_ads_noc.id))  # jornada enviada: diurna
        self.assertIn("grupo", r.context["form"].errors)
        self.assertEqual(Aprendiz.objects.count(), 0)

    def test_grupo_cerrado_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(jornada=self.mixta.id, grupo=self.g_ads_cerrado.id))
        self.assertEqual(Aprendiz.objects.count(), 0)
        self.assertTrue(r.context["form"].errors)

    def test_programa_inactivo_es_rechazado(self):
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(programa_formacion=self.prog_inactivo.id))
        self.assertIn("programa_formacion", r.context["form"].errors)

    def test_campos_nuevos_son_obligatorios(self):
        for campo in ("genero", "telefono", "jornada"):
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

    def test_error_en_grupo_abre_el_paso_2_y_conserva_las_opciones(self):
        r = self.client.post(reverse("usuarios:registro"),
                             self.datos_validos(grupo=self.g_tec_dia.id))
        self.assertEqual(r.context["form"].paso_con_errores(), 2)
        # El <select> de jornada llega lleno desde el servidor (no depende de JS):
        self.assertContains(r, ">Diurna</option>")
        self.assertContains(r, ">Nocturna</option>")

    def test_error_en_datos_personales_abre_el_paso_1(self):
        r = self.client.post(reverse("usuarios:registro"), self.datos_validos(email="no-es-correo"))
        self.assertEqual(r.context["form"].paso_con_errores(), 1)

    def test_usuario_autenticado_es_redirigido(self):
        self.client.post(reverse("usuarios:registro"), self.datos_validos())
        r = self.client.get(reverse("usuarios:registro"))
        self.assertEqual(r.status_code, 302)
