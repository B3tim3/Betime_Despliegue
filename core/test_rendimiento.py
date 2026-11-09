"""Imágenes (5 MB, WebP, miniaturas, huérfanas), periodos y limpieza de datos."""

import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from bienestar.models import MiembroBienestar
from core.services import imagenes, periodos
from core.templatetags.imagenes import miniatura
from actividades.forms import ActividadForm
from actividades.models import Actividad
from notificaciones.models import Notificacion
from publicaciones.models import Publicacion
from usuarios.models import Administrador, IntentoFallido, PersonalBienestar, Usuario

MEDIA = tempfile.mkdtemp(prefix="betime_media_")


def jpeg(ancho=3000, alto=2000, color=(200, 80, 40), exif_orientacion=None, formato="JPEG"):
    buffer = BytesIO()
    imagen = Image.new("RGB", (ancho, alto), color)
    kwargs = {}
    if exif_orientacion:
        exif = Image.Exif()
        exif[0x0112] = exif_orientacion
        kwargs["exif"] = exif
    imagen.save(buffer, format=formato, **kwargs)
    return buffer.getvalue()


def archivo(nombre="foto.jpg", contenido=None, tipo="image/jpeg"):
    return SimpleUploadedFile(nombre, contenido or jpeg(), content_type=tipo)


def ruido(ancho, alto):
    """Imagen de ruido: no se comprime, sirve para fabricar un archivo de más de 5 MB."""
    buffer = BytesIO()
    Image.frombytes("RGB", (ancho, alto), os.urandom(ancho * alto * 3)).save(buffer, format="PNG")
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class ImagenesBase(TestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            numero_documento="2", password="x", tipo_documento="CC",
            nombres="Per", apellidos="Sonal", email="p@x.co")
        PersonalBienestar.objects.create(usuario=cls.usuario, cargo="C", fecha_ingreso=date(2026, 1, 1))

    def actividad(self, **extra):
        ini = timezone.now() + timedelta(days=3)
        datos = dict(titulo="E", lugar="L", horas_otorgadas=1, creado_por=self.usuario,
                     fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2))
        datos.update(extra)
        return Actividad.objects.create(**datos)

    def existe(self, nombre):
        return os.path.exists(os.path.join(MEDIA, nombre))


class OptimizacionTests(ImagenesBase):

    def test_foto_grande_se_reduce_a_webp_con_miniatura(self):
        e = self.actividad(imagen=archivo(contenido=jpeg(4000, 3000)))
        self.assertTrue(e.imagen.name.endswith(".webp"))
        self.assertTrue(self.existe(e.imagen.name))
        self.assertTrue(self.existe(imagenes.nombre_mini(e.imagen.name)))
        with Image.open(os.path.join(MEDIA, e.imagen.name)) as grande:
            self.assertEqual(grande.format, "WEBP")
            self.assertLessEqual(max(grande.size), 1600)
            self.assertEqual(round(grande.size[0] / grande.size[1], 2), round(4000 / 3000, 2))
        with Image.open(os.path.join(MEDIA, imagenes.nombre_mini(e.imagen.name))) as mini:
            self.assertLessEqual(max(mini.size), 480)
        self.assertLess(os.path.getsize(os.path.join(MEDIA, e.imagen.name)), 200 * 1024)

    def test_corrige_la_rotacion_de_fotos_de_celular(self):
        # Foto de 400x200 marcada "girar 90°": debe quedar vertical (200x400).
        e = self.actividad(imagen=archivo(contenido=jpeg(400, 200, exif_orientacion=6)))
        with Image.open(os.path.join(MEDIA, e.imagen.name)) as img:
            self.assertEqual(img.size, (200, 400))

    def test_png_con_transparencia_la_conserva(self):
        buffer = BytesIO()
        Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(buffer, format="PNG")
        e = self.actividad(imagen=archivo("logo.png", buffer.getvalue(), "image/png"))
        with Image.open(os.path.join(MEDIA, e.imagen.name)) as img:
            self.assertEqual(img.mode, "RGBA")

    def test_foto_pequena_no_se_agranda(self):
        e = self.actividad(imagen=archivo(contenido=jpeg(300, 200)))
        with Image.open(os.path.join(MEDIA, e.imagen.name)) as img:
            self.assertEqual(img.size, (300, 200))

    def test_funciona_en_publicaciones_y_equipo(self):
        p = Publicacion.objects.create(autor=self.usuario, titulo="P", contenido="x", imagen=archivo())
        m = MiembroBienestar.objects.create(nombre="Ana", cargo="C", foto=archivo())
        self.assertTrue(p.imagen.name.endswith(".webp") and self.existe(imagenes.nombre_mini(p.imagen.name)))
        self.assertTrue(m.foto.name.endswith(".webp") and self.existe(imagenes.nombre_mini(m.foto.name)))

    def test_guardar_otra_vez_sin_cambios_no_reprocesa_ni_borra(self):
        e = self.actividad(imagen=archivo())
        nombre = e.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            e.titulo = "Otro"
            e.save()
        e.refresh_from_db()
        self.assertEqual(e.imagen.name, nombre)
        self.assertTrue(self.existe(nombre))

    def test_el_cambio_automatico_de_estado_no_toca_imagenes(self):
        e = self.actividad(imagen=archivo())
        nombre = e.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            e.estado = "finalizado"
            e.save(update_fields=["estado"])
        self.assertTrue(self.existe(nombre))


class ArchivosHuerfanosTests(ImagenesBase):

    def test_reemplazar_la_imagen_borra_la_vieja_y_su_miniatura(self):
        e = self.actividad(imagen=archivo())
        vieja = e.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            e.imagen = archivo("nueva.jpg", jpeg(800, 600, (0, 0, 255)))
            e.save()
        self.assertNotEqual(e.imagen.name, vieja)
        self.assertFalse(self.existe(vieja))
        self.assertFalse(self.existe(imagenes.nombre_mini(vieja)))
        self.assertTrue(self.existe(e.imagen.name))

    def test_quitar_la_imagen_borra_los_archivos(self):
        e = self.actividad(imagen=archivo())
        vieja = e.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            e.imagen = None
            e.save()
        self.assertFalse(self.existe(vieja))

    def test_eliminar_el_registro_borra_los_archivos(self):
        e = self.actividad(imagen=archivo())
        nombre = e.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            e.delete()
        self.assertFalse(self.existe(nombre))
        self.assertFalse(self.existe(imagenes.nombre_mini(nombre)))

    def test_no_se_borra_nada_si_la_transaccion_no_se_confirma(self):
        e = self.actividad(imagen=archivo())
        nombre = e.imagen.name
        e.delete()                       # sin ejecutar los on_commit: la BD no confirmó
        self.assertTrue(self.existe(nombre))

    def test_comando_lista_y_borra_huerfanos(self):
        e = self.actividad(imagen=archivo())
        os.makedirs(os.path.join(MEDIA, "actividades"), exist_ok=True)
        huerfano = os.path.join(MEDIA, "actividades", "suelto.webp")
        with open(huerfano, "wb") as f:
            f.write(b"x" * 2048)
        salida = StringIO()
        call_command("limpiar_archivos_huerfanos", stdout=salida)
        self.assertIn("suelto.webp", salida.getvalue())
        self.assertNotIn(os.path.basename(e.imagen.name), salida.getvalue())   # la usada y su mini NO
        self.assertTrue(os.path.exists(huerfano))                              # solo lista
        call_command("limpiar_archivos_huerfanos", "--borrar", stdout=StringIO())
        self.assertFalse(os.path.exists(huerfano))
        self.assertTrue(self.existe(e.imagen.name))
        self.assertTrue(self.existe(imagenes.nombre_mini(e.imagen.name)))


class ValidacionTests(ImagenesBase):

    def datos_actividad(self):
        ini = timezone.now() + timedelta(days=3)
        return {"titulo": "E", "lugar": "L", "horas_otorgadas": 1, "estado": "",
                "fecha_inicio": ini.strftime("%Y-%m-%d %H:%M"),
                "fecha_fin": (ini + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")}

    def test_mas_de_5_mb_se_rechaza_con_mensaje_claro(self):
        grande = ruido(1800, 1800)
        self.assertGreater(len(grande), 5 * 1024 * 1024)
        form = ActividadForm(self.datos_actividad(), {"imagen": archivo("g.png", grande, "image/png")})
        self.assertFalse(form.is_valid())
        self.assertIn("máximo permitido es 5 MB", form.errors["imagen"][0])

    def test_menos_de_5_mb_se_acepta(self):
        form = ActividadForm(self.datos_actividad(), {"imagen": archivo()})
        self.assertTrue(form.is_valid(), form.errors)

    def test_archivo_que_no_es_imagen(self):
        form = ActividadForm(self.datos_actividad(), {"imagen": SimpleUploadedFile("a.jpg", b"no soy imagen", "image/jpeg")})
        self.assertFalse(form.is_valid())

    def test_validar_peso_directo(self):
        class Falso:
            size = 5 * 1024 * 1024 + 1
        with self.assertRaises(Exception):
            imagenes.validar_peso(Falso())
        Falso.size = 5 * 1024 * 1024
        imagenes.validar_peso(Falso())      # justo 5 MB: permitido


class MiniaturaFiltroTests(ImagenesBase):

    def test_usa_miniatura_si_ya_esta_optimizada_y_original_si_es_antigua(self):
        nueva = self.actividad(imagen=archivo())
        self.assertTrue(miniatura(nueva.imagen).endswith("_mini.webp"))
        Actividad.objects.filter(pk=nueva.pk).update(imagen="actividades/antigua.jpg")
        antigua = Actividad.objects.get(pk=nueva.pk)
        self.assertTrue(miniatura(antigua.imagen).endswith("antigua.jpg"))
        self.assertEqual(miniatura(None), "")

    def test_comando_optimizar_imagenes_convierte_las_antiguas(self):
        e = self.actividad()
        os.makedirs(os.path.join(MEDIA, "actividades"), exist_ok=True)
        with open(os.path.join(MEDIA, "actividades", "vieja.jpg"), "wb") as f:
            f.write(jpeg(3000, 2000))
        Actividad.objects.filter(pk=e.pk).update(imagen="actividades/vieja.jpg")

        salida = StringIO()
        call_command("optimizar_imagenes", "--dry-run", stdout=salida)
        self.assertIn("SIMULACIÓN", salida.getvalue())
        self.assertTrue(self.existe("actividades/vieja.jpg"))            # simulación: nada cambia

        call_command("optimizar_imagenes", stdout=StringIO())
        e.refresh_from_db()
        self.assertTrue(e.imagen.name.endswith(".webp"))
        self.assertTrue(self.existe(e.imagen.name) and self.existe(imagenes.nombre_mini(e.imagen.name)))
        self.assertFalse(self.existe("actividades/vieja.jpg"))
        # repetirlo no rompe ni vuelve a procesar
        salida = StringIO()
        call_command("optimizar_imagenes", stdout=salida)
        self.assertIn("Procesadas: 0", salida.getvalue())


# ====================== PERIODOS ======================

class PeriodosServicioTests(TestCase):

    def test_limites_son_el_ano_calendario(self):
        self.assertEqual(periodos.limites(2026), (date(2026, 1, 1), date(2027, 1, 1)))

    def test_resolver(self):
        ahora = timezone.make_aware(datetime(2026, 11, 3, 12))
        vigente = periodos.resolver(None, ahora)
        self.assertEqual((vigente.clave, vigente.desde, vigente.hasta), ("vigente", date(2026, 1, 1), None))
        self.assertTrue(periodos.resolver("todos").es_todos)
        p = periodos.resolver("2025")
        self.assertEqual((p.clave, p.desde, p.hasta), ("2025", date(2025, 1, 1), date(2026, 1, 1)))
        # basura -> vigente, nunca error
        for malo in ("xx", "2025-2", "20255", "1999", "-3", "'; DROP", "2025 "):
            esperado = "2025" if malo == "2025 " else "vigente"
            self.assertEqual(periodos.resolver(malo, ahora).clave, esperado)

    def test_al_llegar_el_nuevo_ano_el_vigente_cambia_solo(self):
        fin = timezone.make_aware(datetime(2026, 12, 31, 23, 0))
        ini = timezone.make_aware(datetime(2027, 1, 1, 1, 0))
        self.assertEqual(periodos.resolver(None, fin).desde, date(2026, 1, 1))
        self.assertEqual(periodos.resolver(None, ini).desde, date(2027, 1, 1))

    def test_opciones_solo_con_anos_que_tienen_registros(self):
        u = Usuario.objects.create_user(
            numero_documento="9", password="x", tipo_documento="CC", nombres="A", apellidos="B", email="z@x.co")
        ahora = timezone.make_aware(datetime(2027, 3, 1, 12))
        # Sin registros: solo vigente y todos
        self.assertEqual([c for c, _ in periodos.opciones(Publicacion.objects.all(), "fecha_creacion", ahora)],
                         ["vigente", "todos"])
        p = Publicacion.objects.create(autor=u, titulo="x", contenido="x")
        Publicacion.objects.filter(pk=p.pk).update(fecha_creacion=timezone.make_aware(datetime(2025, 6, 1)))
        claves = [c for c, _ in periodos.opciones(Publicacion.objects.all(), "fecha_creacion", ahora)]
        self.assertEqual(claves, ["vigente", "2026", "2025", "todos"])
        # Registro del año actual: no agrega años viejos
        Publicacion.objects.filter(pk=p.pk).update(fecha_creacion=timezone.make_aware(datetime(2027, 1, 5)))
        claves = [c for c, _ in periodos.opciones(Publicacion.objects.all(), "fecha_creacion", ahora)]
        self.assertEqual(claves, ["vigente", "todos"])


class PeriodosVistasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.u = Usuario.objects.create_user(
            numero_documento="2", password="x", tipo_documento="CC", nombres="Per", apellidos="S", email="p@x.co")
        PersonalBienestar.objects.create(usuario=cls.u, cargo="C", fecha_ingreso=date(2026, 1, 1))
        hoy = timezone.now()
        inicio, _ = periodos.limites(timezone.localdate().year)
        antes = timezone.make_aware(datetime.combine(inicio - timedelta(days=40), datetime.min.time()))
        cls.viejo = cls._actividad("Actividad VIEJO", antes)
        cls.viejo_anio = timezone.localtime(antes).year
        cls.actual = cls._actividad("Actividad ACTUAL", hoy)
        cls.futuro = cls._actividad("Actividad FUTURO", hoy + timedelta(days=200))
        for titulo, fecha in (("Pub VIEJA", antes), ("Pub ACTUAL", hoy)):
            p = Publicacion.objects.create(autor=cls.u, titulo=titulo, contenido="x")
            Publicacion.objects.filter(pk=p.pk).update(fecha_creacion=fecha)

    @classmethod
    def _actividad(cls, titulo, inicio):
        e = Actividad.objects.create(titulo=titulo, lugar="L", horas_otorgadas=1, creado_por=cls.u,
                                  fecha_inicio=inicio, fecha_fin=inicio + timedelta(hours=1))
        return e

    def cliente(self):
        c = Client()
        c.force_login(self.u)
        return c

    def test_panel_actividades_por_defecto_solo_ano_vigente_y_futuro(self):
        r = self.cliente().get(reverse("actividades:panel_lista"))
        self.assertContains(r, "Actividad ACTUAL")
        self.assertContains(r, "Actividad FUTURO")
        self.assertNotContains(r, "Actividad VIEJO")
        self.assertContains(r, 'name="periodo"')       # hay un actividad viejo => se ofrece el selector
        self.assertContains(r, f'value="{self.viejo_anio}"')

    def test_panel_actividades_todos_y_periodo_especifico(self):
        c = self.cliente()
        self.assertContains(c.get(reverse("actividades:panel_lista") + "?periodo=todos"), "Actividad VIEJO")
        anio = timezone.localtime(self.viejo.fecha_inicio).year
        r = c.get(reverse("actividades:panel_lista") + f"?periodo={anio}")
        self.assertContains(r, "Actividad VIEJO")
        self.assertNotContains(r, "Actividad ACTUAL")

    def test_exportar_respeta_el_periodo(self):
        c = self.cliente()
        r = c.get(reverse("actividades:panel_exportar") + "?formato=excel")
        self.assertEqual(r.status_code, 200)
        from openpyxl import load_workbook
        def titulos(resp):
            hoja = load_workbook(BytesIO(resp.content)).active
            return [str(f[0].value) for f in hoja.iter_rows() if f[0].value]
        self.assertTrue(any("ACTUAL" in t for t in titulos(r)))
        self.assertFalse(any("VIEJO" in t for t in titulos(r)))
        todos = titulos(c.get(reverse("actividades:panel_exportar") + "?formato=excel&periodo=todos"))
        self.assertTrue(any("VIEJO" in t for t in todos))

    def test_panel_publicaciones_por_periodo(self):
        c = self.cliente()
        r = c.get(reverse("publicaciones:panel_lista"))
        self.assertContains(r, "Pub ACTUAL")
        self.assertNotContains(r, "Pub VIEJA")
        self.assertContains(c.get(reverse("publicaciones:panel_lista") + "?periodo=todos"), "Pub VIEJA")

    def test_sin_historial_no_se_muestra_el_selector(self):
        Actividad.objects.filter(pk=self.viejo.pk).delete()
        r = self.cliente().get(reverse("actividades:panel_lista"))
        self.assertNotContains(r, 'name="periodo"')

    def test_periodo_invalido_no_rompe(self):
        r = self.cliente().get(reverse("actividades:panel_lista") + "?periodo=%27%3B--")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Actividad ACTUAL")

    def test_paginacion_conserva_el_periodo(self):
        for i in range(20):
            self._actividad(f"Extra {i}", timezone.now() + timedelta(days=i + 1))
        r = self.cliente().get(reverse("actividades:panel_lista") + "?periodo=vigente")
        self.assertContains(r, "?page=2&periodo=vigente")

    def test_actividades_extracurriculares_por_periodo(self):
        from bienestar.models import ActividadExtracurricular
        pb = self.u.personal_bienestar
        inicio, _ = periodos.limites(timezone.localdate().year)
        ActividadExtracurricular.objects.create(titulo="Act VIEJA", creado_por=pb, fecha=inicio - timedelta(days=30))
        ActividadExtracurricular.objects.create(titulo="Act ACTUAL", creado_por=pb)
        c = self.cliente()
        r = c.get(reverse("bienestar:actividades_lista"))
        self.assertContains(r, "Act ACTUAL")
        self.assertNotContains(r, "Act VIEJA")
        self.assertContains(c.get(reverse("bienestar:actividades_lista") + "?periodo=todos"), "Act VIEJA")


# ====================== LIMPIEZA ======================

class LimpiarDatosTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.u = Usuario.objects.create_user(
            numero_documento="5", password="x", tipo_documento="CC", nombres="A", apellidos="B", email="a@x.co")

    def _notif(self, leida, dias):
        n = Notificacion.objects.create(usuario=self.u, titulo="t", mensaje="m", leida=leida)
        Notificacion.objects.filter(pk=n.pk).update(fecha_creacion=timezone.now() - timedelta(days=dias))
        return n.pk

    def test_borra_solo_lo_que_debe(self):
        leida_vieja = self._notif(True, 100)
        leida_reciente = self._notif(True, 10)
        no_leida_vieja = self._notif(False, 400)       # NUNCA se borra una no leída
        viejo = IntentoFallido.objects.create(numero_documento="1")
        nuevo = IntentoFallido.objects.create(numero_documento="2")
        IntentoFallido.objects.filter(pk=viejo.pk).update(fecha=timezone.now() - timedelta(hours=30))

        salida = StringIO()
        call_command("limpiar_datos", stdout=salida)
        self.assertEqual(sorted(Notificacion.objects.values_list("pk", flat=True)), sorted([leida_reciente, no_leida_vieja]))
        self.assertFalse(Notificacion.objects.filter(pk=leida_vieja).exists())
        self.assertEqual(list(IntentoFallido.objects.values_list("pk", flat=True)), [nuevo.pk])
        self.assertIn("borradas: 1", salida.getvalue())

    def test_dry_run_no_borra(self):
        self._notif(True, 200)
        IntentoFallido.objects.create(numero_documento="1")
        IntentoFallido.objects.update(fecha=timezone.now() - timedelta(days=3))
        salida = StringIO()
        call_command("limpiar_datos", "--dry-run", stdout=salida)
        self.assertEqual(Notificacion.objects.count(), 1)
        self.assertEqual(IntentoFallido.objects.count(), 1)
        self.assertIn("SIMULACIÓN", salida.getvalue())

    def test_dias_configurables(self):
        self._notif(True, 40)
        call_command("limpiar_datos", "--dias-notificaciones", "30", stdout=StringIO())
        self.assertEqual(Notificacion.objects.count(), 0)

    def test_no_toca_la_auditoria(self):
        from core.models import RegistroAuditoria
        RegistroAuditoria.objects.create(accion="asistencia", descripcion="x")
        call_command("limpiar_datos", stdout=StringIO())
        self.assertEqual(RegistroAuditoria.objects.count(), 1)
