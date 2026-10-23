"""
Pruebas de "quién creó" eventos y publicaciones en los paneles de gestión.

Se ejecutan con:   python manage.py test eventos.test_creador
"""

from datetime import date, timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from eventos.models import Evento
from publicaciones.models import Publicacion
from usuarios.models import PersonalBienestar, Usuario


def persona(doc, nombres):
    u = Usuario.objects.create_user(
        numero_documento=doc, password="x", tipo_documento="CC",
        nombres=nombres, apellidos="Gómez", email=f"{doc}@x.co")
    PersonalBienestar.objects.create(usuario=u, cargo="C", fecha_ingreso=date(2026, 1, 1))
    return u


class CreadorTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.laura = persona("10", "Laura")
        cls.mario = persona("11", "Mario")

    def evento(self, creador, titulo):
        ini = timezone.now() + timedelta(days=2)
        return Evento.objects.create(
            titulo=titulo, lugar="Coliseo", creado_por=creador,
            fecha_inicio=ini, fecha_fin=ini + timedelta(hours=1))

    def publicacion(self, autor, titulo):
        return Publicacion.objects.create(autor=autor, titulo=titulo, contenido="x")

    def test_panel_de_eventos_muestra_quien_creo_cada_uno(self):
        self.evento(self.laura, "Yoga")
        self.evento(self.mario, "Cine")
        self.client.force_login(self.laura)
        r = self.client.get(reverse("eventos:panel_lista"))
        self.assertContains(r, "Creado por")
        self.assertContains(r, "Laura Gómez")
        self.assertContains(r, "Mario Gómez")

    def test_panel_de_publicaciones_muestra_quien_creo_cada_una(self):
        self.publicacion(self.laura, "Nota A")
        self.publicacion(self.mario, "Nota B")
        self.client.force_login(self.laura)
        r = self.client.get(reverse("publicaciones:panel_lista"))
        self.assertContains(r, "Creado por")
        self.assertContains(r, "Laura Gómez")
        self.assertContains(r, "Mario Gómez")

    def test_los_paneles_no_hacen_una_consulta_por_fila(self):
        self.client.force_login(self.laura)
        for nombre in ("eventos:panel_lista", "publicaciones:panel_lista",
                       "eventos:panel_exportar", "publicaciones:panel_exportar"):
            self.client.get(reverse(nombre))  # calentar
        self.evento(self.laura, "E1"); self.publicacion(self.laura, "P1")
        pocas = {}
        for nombre in ("eventos:panel_lista", "publicaciones:panel_lista",
                       "eventos:panel_exportar", "publicaciones:panel_exportar"):
            with CaptureQueriesContext(connection) as c:
                self.client.get(reverse(nombre))
            pocas[nombre] = len(c)
        for i in range(12):
            self.evento(self.mario, f"E{i+2}"); self.publicacion(self.mario, f"P{i+2}")
        for nombre, n in pocas.items():
            with CaptureQueriesContext(connection) as c:
                self.client.get(reverse(nombre))
            self.assertEqual(len(c), n, nombre)

    def test_al_editar_se_ve_quien_lo_creo(self):
        ev = self.evento(self.laura, "Yoga")
        pub = self.publicacion(self.mario, "Nota")
        self.client.force_login(self.laura)
        r = self.client.get(reverse("eventos:editar", args=[ev.pk]))
        self.assertContains(r, "Creado por Laura Gómez")
        r = self.client.get(reverse("publicaciones:editar", args=[pub.pk]))
        self.assertContains(r, "Creado por Mario Gómez")

    def test_al_crear_no_aparece_la_linea(self):
        self.client.force_login(self.laura)
        self.assertNotContains(self.client.get(reverse("eventos:crear")), "Creado por")
        self.assertNotContains(self.client.get(reverse("publicaciones:crear")), "Creado por")

    def test_editar_no_cambia_al_creador(self):
        ev = self.evento(self.laura, "Yoga")
        self.client.force_login(self.mario)
        self.client.post(reverse("eventos:editar", args=[ev.pk]), {
            "titulo": "Yoga 2", "descripcion": "", "lugar": "Coliseo", "horas_otorgadas": 1,
            "fecha_inicio": timezone.localtime(ev.fecha_inicio).strftime("%Y-%m-%d %H:%M"),
            "fecha_fin": timezone.localtime(ev.fecha_fin).strftime("%Y-%m-%d %H:%M"),
            "estado": "programado"})
        ev.refresh_from_db()
        self.assertEqual(ev.titulo, "Yoga 2")
        self.assertEqual(ev.creado_por, self.laura)

    def test_el_creador_queda_guardado_al_crear(self):
        self.client.force_login(self.mario)
        ini = timezone.now() + timedelta(days=4)
        self.client.post(reverse("eventos:crear"), {
            "titulo": "Taller", "descripcion": "", "lugar": "Aula", "horas_otorgadas": 1,
            "fecha_inicio": ini.strftime("%Y-%m-%d %H:%M"),
            "fecha_fin": (ini + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "estado": "programado"})
        self.assertEqual(Evento.objects.get(titulo="Taller").creado_por, self.mario)
        self.client.post(reverse("publicaciones:crear"), {
            "titulo": "Aviso", "contenido": "texto", "estado": "borrador"})
        self.assertEqual(Publicacion.objects.get(titulo="Aviso").autor, self.mario)
