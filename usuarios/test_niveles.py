"""
Pruebas del catálogo editable de niveles de formación y del permiso para
administrarlo. Se ejecutan con:   python manage.py test usuarios.test_niveles
"""

from django.test import TestCase
from django.urls import reverse

from usuarios.models import NivelFormacion, ProgramaFormacion, Usuario


class NivelesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser(
            numero_documento="1", password="x", tipo_documento="CC",
            nombres="Admin", apellidos="Be Time",
        )
        cls.aprendiz = Usuario.objects.create_user(
            numero_documento="2", password="x", tipo_documento="CC",
            nombres="Ana", apellidos="Gómez",
        )
        # La migración 0007 ya deja creados "Técnico" y "Tecnólogo".
        cls.tecnico, _ = NivelFormacion.objects.get_or_create(nombre="Técnico")
        cls.tecnologo, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_listado_muestra_niveles_y_cantidad_de_programas(self):
        ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="1", nivel_formacion=self.tecnologo, duracion_meses=24)
        r = self.client.get(reverse("usuarios:niveles_lista"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Técnico")
        totales = {n.nombre: n.total_programas for n in r.context["niveles"]}
        self.assertEqual(totales, {"Técnico": 0, "Tecnólogo": 1})

    def test_crear_nivel(self):
        r = self.client.post(reverse("usuarios:niveles_crear"), {"nombre": "  Especialización   Tecnológica "})
        self.assertRedirects(r, reverse("usuarios:niveles_lista"))
        self.assertTrue(NivelFormacion.objects.filter(nombre="Especialización Tecnológica").exists())

    def test_no_permite_duplicados_sin_importar_mayusculas(self):
        r = self.client.post(reverse("usuarios:niveles_crear"), {"nombre": "técnico"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("nombre", r.context["form"].errors)
        self.assertEqual(NivelFormacion.objects.count(), 2)

    def test_editar_nivel_se_refleja_en_los_programas(self):
        p = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="1", nivel_formacion=self.tecnologo, duracion_meses=24)
        self.client.post(reverse("usuarios:niveles_editar", args=[self.tecnologo.pk]), {"nombre": "Tecnólogo SENA"})
        p.refresh_from_db()
        self.assertEqual(p.nivel_formacion.nombre, "Tecnólogo SENA")

    def test_editar_sin_cambiar_el_nombre_no_da_falso_duplicado(self):
        r = self.client.post(reverse("usuarios:niveles_editar", args=[self.tecnico.pk]), {"nombre": "Técnico"})
        self.assertRedirects(r, reverse("usuarios:niveles_lista"))

    def test_eliminar_nivel_sin_programas(self):
        r = self.client.post(reverse("usuarios:niveles_eliminar", args=[self.tecnico.pk]))
        self.assertRedirects(r, reverse("usuarios:niveles_lista"))
        self.assertFalse(NivelFormacion.objects.filter(pk=self.tecnico.pk).exists())

    def test_eliminar_nivel_en_uso_avisa_y_no_falla(self):
        ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="1", nivel_formacion=self.tecnologo, duracion_meses=24)
        r = self.client.post(reverse("usuarios:niveles_eliminar", args=[self.tecnologo.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(NivelFormacion.objects.filter(pk=self.tecnologo.pk).exists())
        self.assertContains(r, "No se puede eliminar")

    def test_programa_se_guarda_con_el_nivel_elegido(self):
        r = self.client.post(reverse("usuarios:programas_crear"), {
            "nombre": "Nuevo", "codigo": "77", "nivel_formacion": self.tecnico.pk,
            "duracion_meses": 12, "estado": "activo",
        })
        self.assertRedirects(r, reverse("usuarios:programas_lista"))
        self.assertEqual(ProgramaFormacion.objects.get(codigo="77").nivel_formacion, self.tecnico)

    def test_solo_el_administrador_accede(self):
        self.client.force_login(self.aprendiz)
        for nombre in ("niveles_lista", "niveles_crear", "niveles_exportar"):
            r = self.client.get(reverse(f"usuarios:{nombre}"))
            self.assertNotEqual(r.status_code, 200, nombre)
        self.client.logout()
        r = self.client.get(reverse("usuarios:niveles_lista"))
        self.assertNotEqual(r.status_code, 200)

    def test_exportar_excel(self):
        r = self.client.get(reverse("usuarios:niveles_exportar"), {"formato": "excel"})
        self.assertEqual(r.status_code, 200)


class BorradosProtegidosTests(TestCase):
    """
    Eliminar un programa, jornada o grupo que todavía tiene datos
    asociados debe avisar con un mensaje, no fallar con un error 500.
    """

    @classmethod
    def setUpTestData(cls):
        from datetime import date
        from usuarios.models import Aprendiz, Grupo, Jornada

        cls.admin = Usuario.objects.create_superuser(
            numero_documento="1", password="x", tipo_documento="CC",
            nombres="Admin", apellidos="Be Time",
        )
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        cls.jornada = Jornada.objects.create(nombre="Diurna")
        cls.programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="1", nivel_formacion=nivel, duracion_meses=24)
        cls.grupo = Grupo.objects.create(
            numero_grupo="10", programa_formacion=cls.programa, jornada=cls.jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))
        aprendiz = Usuario.objects.create_user(
            numero_documento="2", password="x", tipo_documento="CC",
            nombres="Ana", apellidos="Gómez")
        Aprendiz.objects.create(usuario=aprendiz, grupo=cls.grupo, fecha_ingreso=date(2026, 1, 2))

    def setUp(self):
        self.client.force_login(self.admin)

    def test_no_se_pueden_eliminar_con_datos_asociados(self):
        casos = [
            ("usuarios:jornadas_eliminar", self.jornada, "usuarios:jornadas_lista"),
            ("usuarios:programas_eliminar", self.programa, "usuarios:programas_lista"),
            ("usuarios:grupos_eliminar", self.grupo, "usuarios:grupos_lista"),
        ]
        for nombre, objeto, listado in casos:
            r = self.client.post(reverse(nombre, args=[objeto.pk]), follow=True)
            self.assertEqual(r.status_code, 200, nombre)
            self.assertContains(r, "No se puede eliminar", msg_prefix=nombre)
            self.assertTrue(type(objeto).objects.filter(pk=objeto.pk).exists(), nombre)
