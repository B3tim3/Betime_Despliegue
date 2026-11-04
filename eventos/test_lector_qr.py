"""Pantallas de escaneo: botón «Escanear» con cámara trasera y sin acceso rápido redundante."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bienestar.models import ActividadExtracurricular
from eventos.models import Evento
from usuarios.models import Administrador, PersonalBienestar, Usuario

CLAVE = "x"


class LectorQRTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.u = Usuario.objects.create_user(numero_documento="900", password=CLAVE, tipo_documento="CC",
                                            nombres="Paola", apellidos="R", email="p@x.co")
        cls.pb = PersonalBienestar.objects.create(usuario=cls.u, cargo="C", fecha_ingreso=date(2026, 1, 1))
        ini = timezone.now() + timedelta(days=2)
        cls.evento = Evento.objects.create(titulo="Yoga", lugar="L", horas_otorgadas=1, creado_por=cls.u,
                                           fecha_inicio=ini, fecha_fin=ini + timedelta(hours=1))
        cls.act = ActividadExtracurricular.objects.create(titulo="Uniforme", creado_por=cls.pb)

    def setUp(self):
        self.client.login(numero_documento="900", password=CLAVE)

    def test_escaner_de_eventos_usa_boton_escanear_y_el_script_nuevo(self):
        r = self.client.get(reverse("eventos:escanear_qr"))
        self.assertContains(r, 'id="lector-iniciar"')
        self.assertContains(r, "js/lector-qr.js")
        self.assertContains(r, "iniciarLectorQR(")
        self.assertNotContains(r, "Html5QrcodeScanner")      # el widget viejo con selector de cámara

    def test_escaner_de_extracurriculares_igual(self):
        r = self.client.get(reverse("bienestar:actividad_escanear", args=[self.act.id]))
        self.assertContains(r, 'id="lector-iniciar"')
        self.assertContains(r, "iniciarLectorQR(")
        self.assertNotContains(r, "Html5QrcodeScanner")

    def test_el_script_pide_la_camara_trasera(self):
        from django.contrib.staticfiles import finders
        ruta = finders.find("js/lector-qr.js")
        self.assertIsNotNone(ruta)
        codigo = open(ruta, encoding="utf-8").read()
        self.assertIn('arrancar("environment")', codigo)
        self.assertIn("facingMode", codigo)

    def test_no_se_vuelve_a_pedir_la_camara_tras_abrirla(self):
        """
        Html5Qrcode.getCameras() pide la cámara otra vez; en iPhone (una sola captura a la vez)
        eso congela/cierra el video recién abierto. Solo debe usarse enumerateDevices().
        """
        from django.contrib.staticfiles import finders
        codigo = open(finders.find("js/lector-qr.js"), encoding="utf-8").read()
        sin_comentarios = "\n".join(l for l in codigo.splitlines() if not l.strip().startswith(("//", "*", "/*")))
        self.assertNotIn("getCameras(", sin_comentarios)
        self.assertIn("enumerateDevices", sin_comentarios)

    def test_el_acceso_rapido_generico_ya_no_esta_pero_el_de_cada_evento_si(self):
        r = self.client.get(reverse("usuarios:dashboard_bienestar"))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertNotIn(f'href="{reverse("eventos:escanear_qr")}"', html)
        self.assertIn(f'{reverse("eventos:escanear_qr")}?evento={self.evento.id}', html)


class DetalleHorariosTests(TestCase):
    """El detalle muestra hora de inicio y de fin, cada una con su fecha (los eventos pueden durar varios días)."""

    def test_inicio_y_fin_con_fecha_completa(self):
        u = Usuario.objects.create_user(numero_documento="901", password=CLAVE, tipo_documento="CC",
                                        nombres="P", apellidos="R", email="q@x.co")
        ini = timezone.make_aware(timezone.datetime(2026, 11, 8, 0, 39))
        fin = timezone.make_aware(timezone.datetime(2026, 11, 11, 3, 39))
        e = Evento.objects.create(titulo="Ola", lugar="Paloquemao", horas_otorgadas=60, creado_por=u,
                                  fecha_inicio=ini, fecha_fin=fin)
        r = self.client.get(reverse("eventos:detalle", args=[e.id]))
        self.assertContains(r, "Hora de inicio")
        self.assertContains(r, "08/11/2026 · 12:39 AM")
        self.assertContains(r, "Hora de fin")
        self.assertContains(r, "11/11/2026 · 03:39 AM")
        self.assertNotContains(r, "<small>Horario</small>")


class FormatoHoraTests(TestCase):
    """Todas las horas visibles van en formato de 12 horas con AM/PM."""

    def test_panel_y_exportacion_usan_am_pm(self):
        from io import BytesIO
        from openpyxl import load_workbook
        u = Usuario.objects.create_user(numero_documento="902", password=CLAVE, tipo_documento="CC",
                                        nombres="P", apellidos="R", email="r@x.co")
        PersonalBienestar.objects.create(usuario=u, cargo="C", fecha_ingreso=date(2026, 1, 1))
        ini = timezone.now().replace(hour=15, minute=5, second=0, microsecond=0) + timedelta(days=1)
        e = Evento.objects.create(titulo="Tarde", lugar="L", horas_otorgadas=1, creado_por=u,
                                  fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2))
        self.client.login(numero_documento="902", password=CLAVE)
        esperado = timezone.localtime(e.fecha_inicio).strftime("%d/%m/%Y %I:%M %p")
        self.assertContains(self.client.get(reverse("eventos:panel_lista")), esperado.replace("/", "/"))
        r = self.client.get(reverse("eventos:panel_exportar") + "?formato=excel")
        hoja = load_workbook(BytesIO(r.content)).active
        celdas = [str(c.value) for fila in hoja.iter_rows() for c in fila if c.value]
        self.assertIn(esperado, celdas)
