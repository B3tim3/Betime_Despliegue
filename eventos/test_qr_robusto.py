"""
Pruebas de la robustez del QR y la asistencia:
- no se confirma una inscripción cancelada, un evento cancelado ni con
  demasiada anticipación;
- escanear dos veces el mismo QR no duplica horas;
- el modo de escaneo rápido (JSON) y su "deshacer";
- guardar el checklist no pisa lo que otra persona confirmó con el QR;
- dos confirmaciones al mismo tiempo dejan un solo registro de horas.
"""

import threading
from datetime import date, timedelta

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from bienestar.models import HorasBienestar
from bienestar.services import registrar_asistencia_y_horas
from eventos.models import Asistencia, Evento, Inscripcion
from eventos.services.inscripciones import motivo_no_confirmable
from usuarios.models import (
    Administrador, Aprendiz, Grupo, Jornada, NivelFormacion,
    PersonalBienestar, ProgramaFormacion, Usuario,
)

CLAVE = "Clave-Segura-1"


def _crear_datos(cls, inicio):
    nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
    jornada = Jornada.objects.create(nombre="Diurna")
    programa = ProgramaFormacion.objects.create(
        nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
    grupo = Grupo.objects.create(
        numero_grupo="3000001", programa_formacion=programa, jornada=jornada,
        fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))

    def usuario(doc, nombre):
        return Usuario.objects.create_user(
            numero_documento=doc, password=CLAVE, tipo_documento="CC",
            nombres=nombre, apellidos="Prueba", email=f"{doc}@x.co")

    cls.u_admin = usuario("1", "Admin")
    Administrador.objects.create(usuario=cls.u_admin, fecha_ingreso=date(2026, 1, 1))
    cls.u_personal = usuario("2", "Personal")
    cls.personal = PersonalBienestar.objects.create(
        usuario=cls.u_personal, cargo="C", fecha_ingreso=date(2026, 1, 1))
    cls.u_ap = usuario("3", "Aprendiz")
    cls.aprendiz = Aprendiz.objects.create(usuario=cls.u_ap, grupo=grupo, fecha_ingreso=date(2026, 1, 1))
    cls.evento = Evento.objects.create(
        titulo="Yoga", lugar="Coliseo", horas_otorgadas=2, creado_por=cls.u_personal,
        fecha_inicio=inicio, fecha_fin=inicio + timedelta(hours=2), estado="programado")
    cls.inscripcion = Inscripcion.objects.create(evento=cls.evento, aprendiz=cls.aprendiz)


class ReglaConfirmarTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        _crear_datos(cls, timezone.now() + timedelta(days=3))

    def test_sin_limite_de_horario(self):
        """Se puede confirmar aunque falten días para el evento: no hay ventana de tiempo."""
        self.assertIsNone(motivo_no_confirmable(self.inscripcion))

    def test_inscripcion_cancelada(self):
        Evento.objects.filter(pk=self.evento.pk).update(fecha_inicio=timezone.now())
        Inscripcion.objects.filter(pk=self.inscripcion.pk).update(estado="cancelada")
        self.inscripcion.refresh_from_db()
        self.assertIn("cancelada", motivo_no_confirmable(self.inscripcion))

    def test_evento_cancelado(self):
        Evento.objects.filter(pk=self.evento.pk).update(fecha_inicio=timezone.now(), estado="cancelado")
        self.inscripcion.refresh_from_db()
        self.assertIn("cancelado", motivo_no_confirmable(self.inscripcion))

    def test_la_pantalla_del_qr_confirma_sin_importar_la_hora(self):
        self.client.force_login(self.u_personal)
        self.client.post(reverse("eventos:confirmar_asistencia_qr", args=[self.inscripcion.token]))
        self.assertTrue(Asistencia.objects.get().asistio)
        self.assertEqual(HorasBienestar.objects.get().cantidad_horas, 2)


class ModoRapidoTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        _crear_datos(cls, timezone.now() + timedelta(minutes=30))

    def url(self):
        return reverse("eventos:confirmar_qr_rapido", args=[self.inscripcion.token])

    def test_confirma_y_responde_json(self):
        self.client.force_login(self.u_personal)
        r = self.client.post(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["estado"], "confirmado")
        self.assertEqual(HorasBienestar.objects.get().cantidad_horas, 2)

    def test_escanear_dos_veces_no_duplica(self):
        self.client.force_login(self.u_personal)
        self.client.post(self.url())
        r = self.client.post(self.url())
        self.assertEqual(r.json()["estado"], "ya_estaba")
        self.assertEqual(HorasBienestar.objects.count(), 1)
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_deshacer(self):
        self.client.force_login(self.u_personal)
        self.client.post(self.url())
        r = self.client.post(self.url(), {"accion": "deshacer"})
        self.assertEqual(r.json()["estado"], "deshecho")
        self.assertFalse(Asistencia.objects.get().asistio)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado, "no_asistio")

    def test_admin_y_aprendiz_no(self):
        self.client.force_login(self.u_admin)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        self.client.force_login(self.u_ap)
        self.assertIn(self.client.post(self.url()).status_code, (302, 403))
        self.assertFalse(Asistencia.objects.exists())

    def test_get_no_esta_permitido(self):
        self.client.force_login(self.u_personal)
        self.assertEqual(self.client.get(self.url()).status_code, 405)

    def test_cancelada_responde_409(self):
        Inscripcion.objects.filter(pk=self.inscripcion.pk).update(estado="cancelada")
        self.client.force_login(self.u_personal)
        r = self.client.post(self.url())
        self.assertEqual(r.status_code, 409)
        self.assertFalse(Asistencia.objects.exists())

    def test_token_inexistente(self):
        self.client.force_login(self.u_personal)
        r = self.client.post(reverse("eventos:confirmar_qr_rapido", args=["00000000-0000-0000-0000-000000000000"]))
        self.assertEqual(r.status_code, 404)


class ChecklistNoPisaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        _crear_datos(cls, timezone.now() + timedelta(minutes=30))

    def test_fila_sin_tocar_no_pisa_lo_confirmado_por_qr(self):
        """Se abre el checklist (fila pendiente), alguien confirma por QR, y luego se guarda sin tocar la fila."""
        self.client.force_login(self.u_personal)
        url = reverse("eventos:panel_inscritos", args=[self.evento.pk])
        # Lo que enviaría la página abierta ANTES del QR: pendiente y sin cambios.
        formulario = {f"inicial_{self.inscripcion.pk}": "0"}
        self.client.post(reverse("eventos:confirmar_qr_rapido", args=[self.inscripcion.token]))
        self.client.post(url, formulario)
        self.assertTrue(Asistencia.objects.get().asistio)
        self.assertEqual(HorasBienestar.objects.get().cantidad_horas, 2)

    def test_cambiar_la_fila_si_se_guarda(self):
        self.client.force_login(self.u_personal)
        url = reverse("eventos:panel_inscritos", args=[self.evento.pk])
        pk = self.inscripcion.pk
        self.client.post(url, {f"inicial_{pk}": "0", f"asistio_{pk}": "on", f"horas_{pk}": "3"})
        self.assertEqual(HorasBienestar.objects.get().cantidad_horas, 3)
        # Ahora se corrige a 1 hora: la fila cambió respecto de "1|3".
        self.client.post(url, {f"inicial_{pk}": "1|3", f"asistio_{pk}": "on", f"horas_{pk}": "1"})
        self.assertEqual(HorasBienestar.objects.get().cantidad_horas, 1)

    def test_sin_campo_inicial_funciona_como_antes(self):
        self.client.force_login(self.u_personal)
        url = reverse("eventos:panel_inscritos", args=[self.evento.pk])
        pk = self.inscripcion.pk
        self.client.post(url, {f"asistio_{pk}": "on", f"horas_{pk}": "2"})
        self.assertEqual(HorasBienestar.objects.count(), 1)


class ConcurrenciaTests(TransactionTestCase):
    """Dos confirmaciones simultáneas de la misma inscripción: un solo registro de horas."""

    def setUp(self):
        _crear_datos(self, timezone.now() + timedelta(minutes=30))

    def test_dos_hilos_a_la_vez(self):
        errores = []

        def confirmar():
            try:
                registrar_asistencia_y_horas(
                    inscripcion=Inscripcion.objects.get(pk=self.inscripcion.pk), asistio=True,
                    cantidad_horas=2, motivo="x", asignado_por=PersonalBienestar.objects.get(pk=self.personal.pk),
                    metodo="QR")
            except Exception as e:  # pragma: no cover
                errores.append(e)
            finally:
                connection.close()

        hilos = [threading.Thread(target=confirmar) for _ in range(4)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(errores, [])
        self.assertEqual(Asistencia.objects.count(), 1)
        self.assertEqual(HorasBienestar.objects.count(), 1)


class NavegacionEscanerYPestanasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        _crear_datos(cls, timezone.now() + timedelta(days=1))

    def setUp(self):
        self.client.force_login(self.u_personal)

    def test_escaner_vuelve_al_checklist_del_evento(self):
        r = self.client.get(reverse("eventos:escanear_qr"), {"evento": self.evento.pk})
        self.assertContains(r, reverse("eventos:panel_inscritos", args=[self.evento.pk]))
        self.assertContains(r, "Volver a los inscritos")

    def test_escaner_sin_evento_o_con_dato_malo_vuelve_a_eventos(self):
        for extra in ({}, {"evento": "abc"}, {"evento": "99999"}):
            r = self.client.get(reverse("eventos:escanear_qr"), extra)
            self.assertContains(r, reverse("eventos:panel_lista"))
            self.assertNotContains(r, "Volver a los inscritos")

    def test_checklist_trae_pestanas_con_conteos(self):
        r = self.client.get(reverse("eventos:panel_inscritos", args=[self.evento.pk]))
        self.assertContains(r, 'id="pestanas-checklist"')
        self.assertEqual((r.context["total_pendientes"], r.context["total_asistieron"]), (1, 0))
        self.assertContains(r, 'data-pestana="pendiente"')
        self.assertContains(r, f"?evento={self.evento.pk}")

    def test_conteos_cambian_al_confirmar(self):
        self.client.post(reverse("eventos:confirmar_qr_rapido", args=[self.inscripcion.token]))
        r = self.client.get(reverse("eventos:panel_inscritos", args=[self.evento.pk]))
        self.assertEqual((r.context["total_pendientes"], r.context["total_asistieron"]), (0, 1))
