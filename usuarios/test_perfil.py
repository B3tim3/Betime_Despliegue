"""
Pruebas de "Mi perfil" del aprendiz (editar datos de contacto, formación solo lectura,
cambiar contraseña) y del cambio de grupo por parte de Bienestar.

Se ejecutan con:   python manage.py test usuarios.test_perfil
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from usuarios.forms import PerfilAprendizForm
from usuarios.models import (
    Administrador, Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar,
    ProgramaFormacion, Usuario,
)
from usuarios.services import registrar_aprendiz


class PerfilBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.diurna = Jornada.objects.create(nombre="Diurna")
        cls.nocturna = Jornada.objects.create(nombre="Nocturna")
        cls.tecnologo, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        cls.tecnico, _ = NivelFormacion.objects.get_or_create(nombre="Técnico")

        cls.prog_ads = ProgramaFormacion.objects.create(
            nombre="Análisis y Desarrollo de Software", codigo="228118",
            nivel_formacion=cls.tecnologo, duracion_meses=24)
        cls.prog_tec = ProgramaFormacion.objects.create(
            nombre="Técnico en Sistemas", codigo="111111",
            nivel_formacion=cls.tecnico, duracion_meses=12)

        def grupo(numero, programa, jornada, estado="activa"):
            return Grupo.objects.create(
                numero_grupo=numero, programa_formacion=programa, jornada=jornada,
                fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 12, 31), estado=estado)

        cls.g_dia = grupo("3171693", cls.prog_ads, cls.diurna)
        cls.g_noc = grupo("3171694", cls.prog_ads, cls.nocturna)
        cls.g_cerrado = grupo("3000000", cls.prog_ads, cls.nocturna, estado="cerrada")
        cls.g_tec = grupo("2999999", cls.prog_tec, cls.diurna)

        cls.usuario, cls.aprendiz = registrar_aprendiz(
            tipo_documento="CC", numero_documento="1012345678", nombres="Juan",
            apellidos="Rodríguez", email="juan@example.com", password="ClaveSegura#2026",
            grupo=cls.g_dia, genero="M", telefono="3001234567")
        cls.otro, _ = registrar_aprendiz(
            tipo_documento="CC", numero_documento="1099999999", nombres="Otra",
            apellidos="Persona", email="otra@example.com", password="ClaveSegura#2026",
            grupo=cls.g_dia, genero="F", telefono="3109999999")

    def setUp(self):
        self.client.force_login(self.usuario)
        self.url = reverse("usuarios:perfil")

    def datos(self, **cambios):
        d = {
            "nombres": "Juan", "apellidos": "Rodríguez", "genero": "M",
            "telefono": "3001234567", "email": "juan@example.com",
        }
        d.update(cambios)
        return d

    def recargar(self):
        self.usuario.refresh_from_db()
        self.aprendiz.refresh_from_db()


class AccesoTests(PerfilBase):

    def test_requiere_sesion(self):
        self.client.logout()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("usuarios:login"), r["Location"])

    def test_quien_no_es_aprendiz_es_redirigido(self):
        admin = Usuario.objects.create_user(
            numero_documento="900000001", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Admin", apellidos="Be Time", email="admin@example.com")
        Administrador.objects.create(usuario=admin, fecha_ingreso=date(2026, 1, 1))
        self.client.force_login(admin)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse("usuarios:dashboard"), fetch_redirect_response=False)

    def test_get_muestra_los_datos_actuales(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        for texto in ("1012345678", "Cédula de ciudadanía", "juan@example.com",
                      "3001234567", "Tecnólogo", "3171693"):
            self.assertContains(r, texto)
        # El documento va como campo deshabilitado: no es parte del formulario.
        self.assertNotIn("numero_documento", r.context["form"].fields)

    def test_enlace_en_el_dashboard_y_el_menu(self):
        r = self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertContains(r, self.url)


class EdicionTests(PerfilBase):

    def test_actualiza_datos_personales(self):
        r = self.client.post(self.url, self.datos(
            nombres="  Juan   Camilo ", telefono="+57 300-111-2222",
            email="nuevo@example.com", genero="F"))
        self.assertRedirects(r, self.url, fetch_redirect_response=False)
        self.recargar()
        self.assertEqual(self.usuario.nombres, "Juan Camilo")      # espacios normalizados
        self.assertEqual(self.usuario.telefono, "+573001112222")   # igual que el registro
        self.assertEqual(self.usuario.email, "nuevo@example.com")
        self.assertEqual(self.usuario.genero, "F")
        self.assertEqual(self.aprendiz.grupo, self.g_dia)

    def test_el_documento_no_se_puede_cambiar_ni_por_post_manual(self):
        self.client.post(self.url, self.datos(
            numero_documento="777", tipo_documento="TI", is_staff="on"))
        self.recargar()
        self.assertEqual(self.usuario.numero_documento, "1012345678")
        self.assertEqual(self.usuario.tipo_documento, "CC")
        self.assertFalse(self.usuario.is_staff)

    def test_conservar_el_mismo_correo_es_valido(self):
        r = self.client.post(self.url, self.datos())
        self.assertRedirects(r, self.url, fetch_redirect_response=False)

    def test_correo_de_otra_persona_es_rechazado(self):
        r = self.client.post(self.url, self.datos(email="OTRA@example.com"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("email", r.context["form"].errors)
        self.recargar()
        self.assertEqual(self.usuario.email, "juan@example.com")

    def test_telefono_invalido(self):
        for malo in ("abc", "123"):
            r = self.client.post(self.url, self.datos(telefono=malo))
            self.assertIn("telefono", r.context["form"].errors, malo)

    def test_campos_obligatorios(self):
        for campo in ("nombres", "apellidos", "genero", "telefono", "email"):
            r = self.client.post(self.url, self.datos(**{campo: ""}))
            self.assertIn(campo, r.context["form"].errors, campo)

    def test_genero_solo_masculino_o_femenino(self):
        r = self.client.post(self.url, self.datos(genero="X"))
        self.assertIn("genero", r.context["form"].errors)

    def test_un_error_no_guarda_nada(self):
        self.client.post(self.url, self.datos(nombres="Cambiado", telefono="abc"))
        self.recargar()
        self.assertEqual(self.usuario.nombres, "Juan")


class FormacionSoloLecturaTests(PerfilBase):
    """El aprendiz NO puede cambiar programa, jornada ni grupo (riesgo de errores/fraude)."""

    def test_el_formulario_no_tiene_campos_de_formacion(self):
        campos = PerfilAprendizForm(aprendiz=self.aprendiz).fields
        for prohibido in ("programa_formacion", "jornada", "grupo", "estado", "numero_documento"):
            self.assertNotIn(prohibido, campos)

    def test_la_formacion_se_muestra_pero_deshabilitada(self):
        r = self.client.get(self.url)
        self.assertContains(r, "Análisis y Desarrollo de Software")
        self.assertContains(r, "3171693")
        self.assertContains(r, "solo los modifica el personal de Bienestar")
        self.assertNotContains(r, 'name="grupo"')

    def test_enviar_un_grupo_a_mano_no_lo_cambia(self):
        self.client.post(self.url, self.datos(
            grupo=self.g_noc.id, jornada=self.nocturna.id,
            programa_formacion=self.prog_tec.id, estado="retirado"))
        self.recargar()
        self.assertEqual(self.aprendiz.grupo, self.g_dia)
        self.assertEqual(self.aprendiz.estado, "activo")

    def test_solo_edita_su_propio_perfil(self):
        # No hay forma de indicar a quién se edita: siempre es request.user.
        self.client.post(self.url, self.datos(nombres="Hackeado"))
        self.otro.refresh_from_db()
        self.assertEqual(self.otro.nombres, "Otra")


class PersonalBienestarCambiaElGrupoTests(PerfilBase):
    """Quien sí puede reasignar grupo: personal de Bienestar y administradores."""

    def setUp(self):
        super().setUp()
        self.url_editar = reverse("usuarios:aprendices_editar", args=[self.aprendiz.pk])
        self.bienestar = Usuario.objects.create_user(
            numero_documento="900000002", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Paola", apellidos="Bienestar", email="paola@example.com")
        PersonalBienestar.objects.create(
            usuario=self.bienestar, cargo="Profesional", fecha_ingreso=date(2026, 1, 1))

    def test_bienestar_cambia_el_grupo_de_un_aprendiz(self):
        self.client.force_login(self.bienestar)
        r = self.client.post(self.url_editar, {"grupo": self.g_tec.id, "estado": "activo"})
        self.assertRedirects(r, reverse("usuarios:aprendices_lista"), fetch_redirect_response=False)
        self.recargar()
        self.assertEqual(self.aprendiz.grupo, self.g_tec)

    def test_el_selector_muestra_programa_y_jornada(self):
        self.client.force_login(self.bienestar)
        r = self.client.get(self.url_editar)
        self.assertContains(r, "3171693 — Análisis y Desarrollo de Software · Diurna")
        self.assertContains(r, "3000000 — Análisis y Desarrollo de Software · Nocturna (Cerrado)")

    def test_la_pantalla_dice_a_quien_se_edita(self):
        self.client.force_login(self.bienestar)
        r = self.client.get(self.url_editar)
        self.assertContains(r, "Editar aprendiz: Juan Rodríguez")

    def test_un_aprendiz_no_puede_usar_esa_pantalla(self):
        r = self.client.post(self.url_editar, {"grupo": self.g_tec.id, "estado": "activo"})
        self.assertEqual(r.status_code, 302)
        self.recargar()
        self.assertEqual(self.aprendiz.grupo, self.g_dia)


class ContrasenaTests(PerfilBase):

    def test_cambia_la_contrasena_y_la_sesion_sigue_abierta(self):
        url = reverse("usuarios:cambiar_contrasena")
        r = self.client.post(url, {
            "old_password": "ClaveSegura#2026",
            "new_password1": "OtraClave#2027x", "new_password2": "OtraClave#2027x"})
        self.assertRedirects(r, reverse("usuarios:dashboard"), fetch_redirect_response=False)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("OtraClave#2027x"))
        self.assertEqual(self.client.get(self.url).status_code, 200)   # sigue con sesión

    def test_contrasena_actual_incorrecta(self):
        r = self.client.post(reverse("usuarios:cambiar_contrasena"), {
            "old_password": "mala", "new_password1": "OtraClave#2027x", "new_password2": "OtraClave#2027x"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("old_password", r.context["form"].errors)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("ClaveSegura#2026"))

    def test_contrasena_debil_o_distinta(self):
        url = reverse("usuarios:cambiar_contrasena")
        r = self.client.post(url, {"old_password": "ClaveSegura#2026",
                                   "new_password1": "12345678", "new_password2": "12345678"})
        self.assertTrue(r.context["form"].errors)
        r = self.client.post(url, {"old_password": "ClaveSegura#2026",
                                   "new_password1": "OtraClave#2027x", "new_password2": "distinta"})
        self.assertIn("new_password2", r.context["form"].errors)

    def test_requiere_sesion(self):
        self.client.logout()
        r = self.client.get(reverse("usuarios:cambiar_contrasena"))
        self.assertEqual(r.status_code, 302)
