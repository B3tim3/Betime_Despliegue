from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from publicaciones.models import Publicacion
from publicaciones.views import _minutos_lectura
from usuarios.models import Usuario


class PublicacionesPublicasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user(
            numero_documento="9", password="Clave-Segura-1", tipo_documento="CC",
            nombres="Paola", apellidos="Ramírez", email="p@x.co")
        ahora = timezone.now()
        for i in range(12):
            Publicacion.objects.create(
                autor=cls.autor, titulo=f"Noticia {i}", contenido=f"Contenido de la noticia {i} " * 10,
                estado="publicado", fecha_publicacion=ahora - timedelta(days=i))
        Publicacion.objects.create(
            autor=cls.autor, titulo="Borrador oculto", contenido="x", estado="borrador")

    def test_minutos_de_lectura(self):
        self.assertEqual(_minutos_lectura("hola mundo"), 1)
        self.assertEqual(_minutos_lectura("palabra " * 600), 3)

    def test_lista_destaca_la_mas_reciente_y_pagina(self):
        r = self.client.get(reverse("publicaciones:lista"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["destacada"].titulo, "Noticia 0")
        self.assertEqual(len(r.context["resto"]), 9)
        self.assertNotContains(r, "Borrador oculto")
        self.assertContains(r, "Siguiente")

    def test_segunda_pagina_no_destaca(self):
        r = self.client.get(reverse("publicaciones:lista"), {"page": 2})
        self.assertIsNone(r.context["destacada"])
        self.assertEqual(len(r.context["resto"]), 2)

    def test_buscador(self):
        r = self.client.get(reverse("publicaciones:lista"), {"q": "noticia 7"})
        self.assertEqual(r.context["pagina"].paginator.count, 1)
        self.assertIsNone(r.context["destacada"])
        r = self.client.get(reverse("publicaciones:lista"), {"q": "zzzz"})
        self.assertContains(r, "No encontramos publicaciones")

    def test_detalle_muestra_otras_y_no_publica_borradores(self):
        pub = Publicacion.objects.get(titulo="Noticia 3")
        r = self.client.get(reverse("publicaciones:detalle", args=[pub.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["otras"]), 3)
        self.assertNotIn(pub, list(r.context["otras"]))
        borrador = Publicacion.objects.get(titulo="Borrador oculto")
        self.assertEqual(self.client.get(reverse("publicaciones:detalle", args=[borrador.pk])).status_code, 404)

    def test_sin_publicaciones(self):
        Publicacion.objects.all().delete()
        r = self.client.get(reverse("publicaciones:lista"))
        self.assertContains(r, "Todavía no hay publicaciones")
