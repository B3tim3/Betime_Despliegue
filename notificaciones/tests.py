"""
Pruebas del Paquete 3: inscribirse / cancelar desde el panel,
notificaciones (campanita) y recordatorios.

Se ejecutan con:   python manage.py test notificaciones
"""

import os
from datetime import date, timedelta
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from bienestar.services import registrar_asistencia_y_horas
from eventos.models import Evento, Inscripcion
from eventos.services.inscripciones import InscripcionError, cancelar, inscribir
from notificaciones.models import Notificacion
from notificaciones.services import notificar, notificar_muchos
from notificaciones.services.recordatorios import enviar_recordatorios
from usuarios.models import (
    Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar,
    ProgramaFormacion, Usuario,
)

CLAVE = "x"


def crear_aprendiz(doc, grupo, email=None):
    u = Usuario.objects.create_user(
        numero_documento=doc, password=CLAVE, tipo_documento="CC",
        nombres=f"Ana{doc}", apellidos="Pérez", email=email if email is not None else f"a{doc}@x.co")
    return Aprendiz.objects.create(usuario=u, grupo=grupo, fecha_ingreso=date(2026, 1, 1))


class Base(TestCase):

    @classmethod
    def setUpTestData(cls):
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        jor = Jornada.objects.create(nombre="Diurna")
        prog = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
        cls.grupo = Grupo.objects.create(
            numero_grupo="3000001", programa_formacion=prog, jornada=jor,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))
        cls.staff_u = Usuario.objects.create_user(
            numero_documento="900", password=CLAVE, tipo_documento="CC",
            nombres="Paola", apellidos="Ramírez", email="p@x.co")
        cls.staff = PersonalBienestar.objects.create(
            usuario=cls.staff_u, cargo="Coordinadora", fecha_ingreso=date(2026, 1, 1))
        cls.ap1 = crear_aprendiz("101", cls.grupo)
        cls.ap2 = crear_aprendiz("102", cls.grupo)

    def evento(self, titulo="Yoga", dias=3, estado="programado", horas=2):
        ini = timezone.now() + timedelta(days=dias)
        return Evento.objects.create(
            titulo=titulo, lugar="Coliseo", horas_otorgadas=horas, creado_por=self.staff_u,
            fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2), estado=estado)

    def login(self, doc):
        self.client.login(numero_documento=doc, password=CLAVE)


class InscribirYCancelarTests(Base):

    def test_inscribir_crea_inscripcion_y_notifica(self):
        ev = self.evento()
        insc, accion = inscribir(self.ap1, ev)
        self.assertEqual(accion, "creada")
        self.assertEqual(insc.estado, "inscrito")
        n = Notificacion.objects.get(usuario=self.ap1.usuario)
        self.assertEqual(n.tipo, "inscripcion")
        self.assertEqual(n.url, f"/eventos/{ev.id}/")

    def test_inscribir_dos_veces_no_duplica_ni_renotifica(self):
        ev = self.evento()
        inscribir(self.ap1, ev)
        _, accion = inscribir(self.ap1, ev)
        self.assertEqual(accion, "existente")
        self.assertEqual(Inscripcion.objects.count(), 1)
        self.assertEqual(Notificacion.objects.count(), 1)

    def test_evento_cerrado_no_permite_inscribirse(self):
        ev = self.evento(estado="finalizado")
        with self.assertRaises(InscripcionError):
            inscribir(self.ap1, ev)

    def test_cancelar_y_reinscribirse_reactiva_con_token_nuevo(self):
        ev = self.evento()
        insc, _ = inscribir(self.ap1, ev)
        token_viejo = insc.token
        cancelar(insc)
        insc.refresh_from_db()
        self.assertEqual(insc.estado, "cancelada")

        insc2, accion = inscribir(self.ap1, ev)
        self.assertEqual(accion, "reactivada")
        self.assertEqual(insc2.pk, insc.pk)           # misma fila: unique_together
        self.assertEqual(insc2.estado, "inscrito")
        self.assertNotEqual(insc2.token, token_viejo)  # el QR viejo ya no sirve
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_no_se_puede_cancelar_evento_que_ya_empezo(self):
        ev = self.evento(dias=-1)
        insc = Inscripcion.objects.create(evento=ev, aprendiz=self.ap1)
        with self.assertRaises(InscripcionError):
            cancelar(insc)

    def test_no_se_puede_cancelar_si_ya_tiene_asistencia(self):
        ev = self.evento()
        insc = Inscripcion.objects.create(evento=ev, aprendiz=self.ap1)
        registrar_asistencia_y_horas(inscripcion=insc, asistio=True, cantidad_horas=2,
                                     motivo="x", asignado_por=self.staff)
        insc.refresh_from_db()
        with self.assertRaises(InscripcionError):
            cancelar(insc)

    def test_vista_cancelar_pide_post(self):
        ev = self.evento()
        insc, _ = inscribir(self.ap1, ev)
        self.login("101")
        r = self.client.get(reverse("eventos:cancelar_inscripcion", args=[insc.id]))
        self.assertEqual(r.status_code, 405)

    def test_vista_cancelar_funciona_y_vuelve_al_panel(self):
        ev = self.evento()
        insc, _ = inscribir(self.ap1, ev)
        self.login("101")
        r = self.client.post(
            reverse("eventos:cancelar_inscripcion", args=[insc.id]),
            {"next": reverse("usuarios:dashboard_aprendiz")})
        self.assertRedirects(r, reverse("usuarios:dashboard_aprendiz"))
        insc.refresh_from_db()
        self.assertEqual(insc.estado, "cancelada")
        self.assertTrue(Notificacion.objects.filter(usuario=self.ap1.usuario, tipo="cancelacion").exists())

    def test_no_se_puede_cancelar_la_inscripcion_de_otro(self):
        ev = self.evento()
        insc, _ = inscribir(self.ap1, ev)
        self.login("102")
        r = self.client.post(reverse("eventos:cancelar_inscripcion", args=[insc.id]))
        self.assertEqual(r.status_code, 404)
        insc.refresh_from_db()
        self.assertEqual(insc.estado, "inscrito")

    def test_next_externo_se_ignora(self):
        ev = self.evento()
        insc, _ = inscribir(self.ap1, ev)
        self.login("101")
        r = self.client.post(reverse("eventos:cancelar_inscripcion", args=[insc.id]),
                             {"next": "https://malo.example.com/"})
        self.assertRedirects(r, reverse("usuarios:dashboard_aprendiz"))

    def test_vista_inscribirse_desde_panel_y_reinscripcion(self):
        ev = self.evento()
        self.login("101")
        url = reverse("eventos:inscribirse", args=[ev.id])
        nxt = {"next": reverse("usuarios:dashboard_aprendiz")}
        r = self.client.post(url, nxt)
        self.assertRedirects(r, reverse("usuarios:dashboard_aprendiz"))
        insc = Inscripcion.objects.get()
        self.client.post(reverse("eventos:cancelar_inscripcion", args=[insc.id]))
        self.client.post(url, nxt)
        insc.refresh_from_db()
        self.assertEqual(insc.estado, "inscrito")

    def test_qr_de_inscripcion_cancelada_no_se_muestra(self):
        ev = self.evento()
        insc, _ = inscribir(self.ap1, ev)
        cancelar(insc)
        self.login("101")
        r = self.client.get(reverse("eventos:mi_qr", args=[insc.id]))
        self.assertRedirects(r, reverse("usuarios:dashboard_aprendiz"))

    def test_detalle_muestra_cancelar_solo_si_inscrito(self):
        ev = self.evento()
        self.login("101")
        r = self.client.get(reverse("eventos:detalle", args=[ev.id]))
        self.assertNotContains(r, "Cancelar inscripción")
        inscribir(self.ap1, ev)
        r = self.client.get(reverse("eventos:detalle", args=[ev.id]))
        self.assertContains(r, "Cancelar inscripción")

    def test_panel_muestra_proximos_eventos_sin_los_ya_inscritos(self):
        a = self.evento("Evento A")
        self.evento("Evento B")
        inscribir(self.ap1, a)
        self.login("101")
        r = self.client.get(reverse("usuarios:dashboard_aprendiz"))
        nombres = [e.titulo for e in r.context["proximos_eventos"]]
        self.assertEqual(nombres, ["Evento B"])
        # tras cancelar, vuelve a aparecer
        cancelar(Inscripcion.objects.get(evento=a))
        r = self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertEqual(len(r.context["proximos_eventos"]), 2)


class NotificacionesTests(Base):

    def test_notificar_muchos_sin_repetidos(self):
        n = notificar_muchos([self.ap1.usuario_id, self.ap1.usuario_id, self.ap2.usuario_id], "T", "M")
        self.assertEqual(n, 2)
        self.assertEqual(Notificacion.objects.count(), 2)

    def test_titulo_largo_se_recorta(self):
        n = notificar(self.ap1.usuario, "x" * 400, "m")
        self.assertEqual(len(n.titulo), 150)

    def test_campanita_muestra_cantidad(self):
        notificar(self.ap1.usuario, "Uno", "m")
        notificar(self.ap1.usuario, "Dos", "m")
        self.login("101")
        r = self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertContains(r, "2 sin leer")

    def test_campanita_una_sola_consulta_aunque_haya_muchas(self):
        self.login("101")
        self.client.get(reverse("usuarios:dashboard_aprendiz"))  # calentar
        with CaptureQueriesContext(connection) as pocas:
            self.client.get(reverse("usuarios:dashboard_aprendiz"))
        notificar_muchos([self.ap1.usuario_id] * 1, "T", "M")
        for _ in range(30):
            notificar(self.ap1.usuario, "T", "M")
        with CaptureQueriesContext(connection) as muchas:
            self.client.get(reverse("usuarios:dashboard_aprendiz"))
        self.assertEqual(len(pocas), len(muchas))

    def test_lista_solo_muestra_las_propias(self):
        notificar(self.ap1.usuario, "Mía", "m")
        notificar(self.ap2.usuario, "Ajena", "m")
        self.login("101")
        r = self.client.get(reverse("notificaciones:lista"))
        self.assertContains(r, "Mía")
        self.assertNotContains(r, "Ajena")

    def test_lista_requiere_sesion(self):
        r = self.client.get(reverse("notificaciones:lista"))
        self.assertEqual(r.status_code, 302)

    def test_abrir_marca_leida_y_redirige(self):
        n = notificar(self.ap1.usuario, "T", "m", url="/eventos/")
        self.login("101")
        r = self.client.get(reverse("notificaciones:abrir", args=[n.id]), follow=False)
        self.assertRedirects(r, "/eventos/", fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.leida)

    def test_abrir_no_redirige_fuera_del_sitio(self):
        for destino in ("https://malo.example.com", "//malo.example.com"):
            n = notificar(self.ap1.usuario, "T", "m", url=destino)
            self.login("101")
            r = self.client.get(reverse("notificaciones:abrir", args=[n.id]))
            self.assertRedirects(r, reverse("notificaciones:lista"))

    def test_no_se_puede_abrir_la_de_otro(self):
        n = notificar(self.ap2.usuario, "T", "m")
        self.login("101")
        r = self.client.get(reverse("notificaciones:abrir", args=[n.id]))
        self.assertEqual(r.status_code, 404)
        n.refresh_from_db()
        self.assertFalse(n.leida)

    def test_marcar_todas_solo_afecta_a_las_propias(self):
        a = notificar(self.ap1.usuario, "A", "m")
        b = notificar(self.ap2.usuario, "B", "m")
        self.login("101")
        self.client.post(reverse("notificaciones:marcar_todas"))
        a.refresh_from_db(); b.refresh_from_db()
        self.assertTrue(a.leida)
        self.assertFalse(b.leida)

    def test_filtro_solo_no_leidas(self):
        n = notificar(self.ap1.usuario, "Vieja", "m")
        n.leida = True; n.save()
        notificar(self.ap1.usuario, "Nueva", "m")
        self.login("101")
        r = self.client.get(reverse("notificaciones:lista") + "?solo=no_leidas")
        self.assertContains(r, "Nueva")
        self.assertNotContains(r, "Vieja")

    def test_mensaje_con_html_se_escapa(self):
        notificar(self.ap1.usuario, "<script>alert(1)</script>", "<b>x</b>")
        self.login("101")
        r = self.client.get(reverse("notificaciones:lista"))
        self.assertNotContains(r, "<script>alert(1)</script>")

    # ----- disparadores desde Bienestar -----

    def test_horas_registradas_notifican_una_sola_vez(self):
        ev = self.evento()
        insc = Inscripcion.objects.create(evento=ev, aprendiz=self.ap1)
        kw = dict(inscripcion=insc, asistio=True, cantidad_horas=2, motivo="x", asignado_por=self.staff)
        registrar_asistencia_y_horas(**kw)
        registrar_asistencia_y_horas(**kw)  # guardar el checklist de nuevo
        self.assertEqual(Notificacion.objects.filter(tipo="horas").count(), 1)
        registrar_asistencia_y_horas(**{**kw, "cantidad_horas": 3})  # corrección
        self.assertEqual(Notificacion.objects.filter(tipo="horas").count(), 2)

    def test_evento_nuevo_avisa_a_todos_los_aprendices(self):
        self.login("900")
        ini = timezone.now() + timedelta(days=5)
        r = self.client.post(reverse("eventos:crear"), {
            "titulo": "Taller", "descripcion": "", "lugar": "Aula 1", "horas_otorgadas": 2,
            "fecha_inicio": ini.strftime("%Y-%m-%d %H:%M"),
            "fecha_fin": (ini + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
            "estado": "programado"})
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        self.assertEqual(Notificacion.objects.filter(tipo="evento").count(), 2)
        self.assertFalse(Notificacion.objects.filter(usuario=self.staff_u).exists())

    def _editar(self, ev, **cambios):
        datos = {
            "titulo": ev.titulo, "descripcion": "", "lugar": ev.lugar, "horas_otorgadas": ev.horas_otorgadas,
            "fecha_inicio": timezone.localtime(ev.fecha_inicio).strftime("%Y-%m-%d %H:%M"),
            "fecha_fin": timezone.localtime(ev.fecha_fin).strftime("%Y-%m-%d %H:%M"),
            "estado": ev.estado,
        }
        datos.update(cambios)
        self.login("900")
        return self.client.post(reverse("eventos:editar", args=[ev.pk]), datos)

    def test_cancelar_evento_avisa_solo_a_inscritos_activos(self):
        ev = self.evento()
        inscribir(self.ap1, ev)
        Notificacion.objects.all().delete()
        r = self._editar(ev, estado="cancelado")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Notificacion.objects.count(), 1)
        n = Notificacion.objects.get()
        self.assertEqual(n.usuario, self.ap1.usuario)
        self.assertIn("cancelado", n.titulo.lower())

    def test_cambio_de_lugar_avisa_y_sin_cambios_no_avisa(self):
        ev = self.evento()
        inscribir(self.ap1, ev)
        Notificacion.objects.all().delete()
        self._editar(ev)  # no cambia nada que afecte
        self.assertEqual(Notificacion.objects.count(), 0)
        self._editar(ev, lugar="Auditorio")
        n = Notificacion.objects.get()
        self.assertIn("Auditorio", n.mensaje)

    def test_cambio_de_fecha_reinicia_el_recordatorio(self):
        ev = self.evento(dias=1)
        insc, _ = inscribir(self.ap1, ev)
        Inscripcion.objects.filter(pk=insc.pk).update(recordatorio_enviado=True)
        nueva = timezone.localtime(ev.fecha_inicio) + timedelta(days=2)
        self._editar(ev, fecha_inicio=nueva.strftime("%Y-%m-%d %H:%M"),
                     fecha_fin=(nueva + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"))
        insc.refresh_from_db()
        self.assertFalse(insc.recordatorio_enviado)

    def test_eliminar_evento_futuro_avisa_a_inscritos(self):
        ev = self.evento()
        inscribir(self.ap1, ev)
        Notificacion.objects.all().delete()
        self.login("900")
        self.client.post(reverse("eventos:eliminar", args=[ev.pk]))
        self.assertFalse(Evento.objects.filter(pk=ev.pk).exists())
        self.assertEqual(Notificacion.objects.filter(usuario=self.ap1.usuario, tipo="cancelacion").count(), 1)


class RecordatoriosTests(Base):

    def test_recuerda_solo_lo_que_empieza_pronto(self):
        cerca = self.evento("Cerca", dias=0)
        cerca.fecha_inicio = timezone.now() + timedelta(hours=5); cerca.save()
        lejos = self.evento("Lejos", dias=10)
        inscribir(self.ap1, cerca)
        inscribir(self.ap1, lejos)
        Notificacion.objects.all().delete()

        r = enviar_recordatorios(horas=24)
        self.assertEqual(r["recordatorios"], 1)
        self.assertEqual(r["correos"], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Cerca", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["a101@x.co"])
        self.assertEqual(Notificacion.objects.get().tipo, "recordatorio")

    def test_no_repite_el_recordatorio(self):
        ev = self.evento(); ev.fecha_inicio = timezone.now() + timedelta(hours=3); ev.save()
        inscribir(self.ap1, ev)
        enviar_recordatorios()
        r = enviar_recordatorios()
        self.assertEqual(r["recordatorios"], 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_ignora_canceladas_y_eventos_cancelados_o_pasados(self):
        ev1 = self.evento("A"); ev1.fecha_inicio = timezone.now() + timedelta(hours=3); ev1.save()
        ev2 = self.evento("B", estado="cancelado"); ev2.fecha_inicio = timezone.now() + timedelta(hours=3); ev2.save()
        ev3 = self.evento("C", dias=-1)
        i1, _ = inscribir(self.ap1, ev1); cancelar(i1)
        Inscripcion.objects.create(evento=ev2, aprendiz=self.ap1)
        Inscripcion.objects.create(evento=ev3, aprendiz=self.ap1)
        self.assertEqual(enviar_recordatorios()["recordatorios"], 0)

    def test_sin_correo_registrado_igual_crea_campanita(self):
        ap = crear_aprendiz("103", self.grupo, email="")
        ev = self.evento(); ev.fecha_inicio = timezone.now() + timedelta(hours=3); ev.save()
        Inscripcion.objects.create(evento=ev, aprendiz=ap)
        r = enviar_recordatorios()
        self.assertEqual((r["recordatorios"], r["correos"], r["sin_correo"]), (1, 0, 1))

    def test_correo_que_falla_no_frena_ni_repite(self):
        ev = self.evento(); ev.fecha_inicio = timezone.now() + timedelta(hours=3); ev.save()
        Inscripcion.objects.create(evento=ev, aprendiz=self.ap1)
        Inscripcion.objects.create(evento=ev, aprendiz=self.ap2)
        with mock.patch("django.core.mail.message.EmailMessage.send", side_effect=[Exception("smtp caído"), 1]):
            r = enviar_recordatorios()
        self.assertEqual((r["recordatorios"], r["fallidos"], r["correos"]), (2, 1, 1))
        self.assertEqual(enviar_recordatorios()["recordatorios"], 0)  # no reintenta la campanita

    def test_sin_correo_flag_y_comando(self):
        ev = self.evento(); ev.fecha_inicio = timezone.now() + timedelta(hours=3); ev.save()
        Inscripcion.objects.create(evento=ev, aprendiz=self.ap1)
        call_command("enviar_recordatorios", "--sin-correo", stdout=mock.MagicMock())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(Notificacion.objects.filter(tipo="recordatorio").count(), 1)

    def test_reinscripcion_permite_nuevo_recordatorio(self):
        ev = self.evento(); ev.fecha_inicio = timezone.now() + timedelta(hours=3); ev.save()
        insc, _ = inscribir(self.ap1, ev)
        enviar_recordatorios()
        cancelar(insc)
        inscribir(self.ap1, ev)
        self.assertEqual(enviar_recordatorios()["recordatorios"], 1)

    # ----- endpoint para cron externo -----

    def test_endpoint_apagado_sin_token_configurado(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RECORDATORIOS_TOKEN", None)
            r = self.client.get(reverse("notificaciones:ejecutar_recordatorios") + "?token=lo-que-sea")
        self.assertEqual(r.status_code, 404)

    def test_endpoint_exige_token_correcto(self):
        url = reverse("notificaciones:ejecutar_recordatorios")
        with mock.patch.dict(os.environ, {"RECORDATORIOS_TOKEN": "secreto123"}):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.get(url + "?token=mal").status_code, 403)
            ok = self.client.get(url + "?token=secreto123")
            self.assertEqual(ok.status_code, 200)
            self.assertIn("recordatorios", ok.json())
            ok2 = self.client.get(url, HTTP_AUTHORIZATION="Bearer secreto123")
            self.assertEqual(ok2.status_code, 200)
