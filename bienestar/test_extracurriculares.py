"""Horas de bienestar por mérito: código, QR personal, checklist, conteo unificado y permisos."""

from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from bienestar.models import (
    ActividadExtracurricular, ConstanciaHoras, HorasBienestar, ParticipacionExtracurricular,
)
from bienestar.services import extracurriculares as svc
from bienestar.services.constancia import emitir_constancia, generar_pdf_constancia
from bienestar.services.historial import historial_extracurricular_de
from bienestar.services.progreso import horas_de, total_horas_de
from eventos.models import Evento, Inscripcion
from notificaciones.models import Notificacion
from usuarios.models import (
    Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar, ProgramaFormacion, Usuario,
)


class Base(TestCase):

    @classmethod
    def setUpTestData(cls):
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        jornada = Jornada.objects.create(nombre="Diurna")
        programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
        grupo = Grupo.objects.create(
            numero_grupo="3000001", programa_formacion=programa, jornada=jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))

        def usuario(doc, nombre):
            return Usuario.objects.create_user(
                numero_documento=doc, password="x", tipo_documento="CC",
                nombres=nombre, apellidos="Prueba", email=f"{doc}@x.co")

        cls.u_personal = usuario("2", "Personal")
        cls.personal = PersonalBienestar.objects.create(
            usuario=cls.u_personal, cargo="C", fecha_ingreso=date(2026, 1, 1))
        cls.u_ap = usuario("3", "Ana")
        cls.ap = Aprendiz.objects.create(usuario=cls.u_ap, grupo=grupo, fecha_ingreso=date(2026, 1, 1))
        cls.u_ap2 = usuario("4", "Luis")
        cls.ap2 = Aprendiz.objects.create(usuario=cls.u_ap2, grupo=grupo, fecha_ingreso=date(2026, 1, 1))
        cls.act = ActividadExtracurricular.objects.create(
            titulo="Uniforme", horas=2, creado_por=cls.personal)

    def cliente(self, usuario):
        c = Client()
        c.force_login(usuario)
        return c


class CodigoTests(Base):

    def test_codigo_unico_y_legible(self):
        otra = ActividadExtracurricular.objects.create(titulo="Otra", creado_por=self.personal)
        self.assertEqual(len(self.act.codigo), 6)
        self.assertNotEqual(self.act.codigo, otra.codigo)
        self.assertFalse(set(self.act.codigo) & set("01OIL"))

    def test_aprendiz_entra_con_codigo_y_queda_pendiente(self):
        r = self.cliente(self.u_ap).post(reverse("bienestar:recibir_extracurriculares"),
                                         {"codigo": f" {self.act.codigo.lower()} "})
        self.assertEqual(r.status_code, 302)
        p = ParticipacionExtracurricular.objects.get(actividad=self.act, aprendiz=self.ap)
        self.assertEqual((p.estado, p.metodo), ("pendiente", "codigo"))
        self.assertEqual(total_horas_de(self.ap), 0)

    def test_codigo_repetido_no_duplica(self):
        svc.unirse_con_codigo(self.ap, self.act.codigo)
        _, creada = svc.unirse_con_codigo(self.ap, self.act.codigo)
        self.assertFalse(creada)
        self.assertEqual(ParticipacionExtracurricular.objects.count(), 1)

    def test_codigo_invalido_o_actividad_cerrada(self):
        with self.assertRaises(svc.ExtracurricularError):
            svc.unirse_con_codigo(self.ap, "ZZZZZZ")
        with self.assertRaises(svc.ExtracurricularError):
            svc.unirse_con_codigo(self.ap, "")
        self.act.estado = "cerrada"
        self.act.save()
        with self.assertRaises(svc.ExtracurricularError):
            svc.unirse_con_codigo(self.ap, self.act.codigo)

    def test_checklist_otorga_y_quita_horas(self):
        p, _ = svc.unirse_con_codigo(self.ap, self.act.codigo)
        c = self.cliente(self.u_personal)
        url = reverse("bienestar:actividad_detalle", args=[self.act.id])
        c.post(url, {f"inicial_{p.id}": "0", f"dar_{p.id}": "on", f"horas_{p.id}": "3"})
        p.refresh_from_db()
        self.assertEqual(p.estado, "otorgada")
        self.assertEqual(total_horas_de(self.ap), 3)
        self.assertTrue(Notificacion.objects.filter(usuario=self.u_ap, tipo="horas").exists())

        # Guardar de nuevo lo mismo no cambia nada ni duplica.
        c.post(url, {f"inicial_{p.id}": "1|3", f"dar_{p.id}": "on", f"horas_{p.id}": "3"})
        self.assertEqual(HorasBienestar.objects.count(), 1)

        # Desmarcar: deja de contar, pero el registro queda.
        c.post(url, {f"inicial_{p.id}": "1|3", f"horas_{p.id}": "3"})
        p.refresh_from_db()
        self.assertEqual(p.estado, "pendiente")
        self.assertEqual(total_horas_de(self.ap), 0)
        self.assertEqual(HorasBienestar.objects.count(), 1)

    def test_fila_sin_tocar_no_pisa_lo_que_hizo_el_qr(self):
        p, _ = svc.unirse_con_codigo(self.ap, self.act.codigo)
        # La página se abrió con la fila pendiente ("0"); mientras tanto el QR dio horas.
        svc.otorgar_horas(actividad=self.act, aprendiz=self.ap, horas=2,
                          asignado_por=self.personal, metodo="qr")
        self.cliente(self.u_personal).post(
            reverse("bienestar:actividad_detalle", args=[self.act.id]),
            {f"inicial_{p.id}": "0", f"horas_{p.id}": "2"})
        p.refresh_from_db()
        self.assertEqual(p.estado, "otorgada")

    def test_agregar_por_documento(self):
        c = self.cliente(self.u_personal)
        url = reverse("bienestar:actividad_agregar", args=[self.act.id])
        c.post(url, {"documento": "4"})
        self.assertTrue(ParticipacionExtracurricular.objects.filter(aprendiz=self.ap2, metodo="manual").exists())
        c.post(url, {"documento": "999"})
        self.assertEqual(ParticipacionExtracurricular.objects.count(), 1)


class QrTests(Base):

    def test_token_firmado(self):
        token = svc.token_qr_de(self.ap)
        self.assertEqual(svc.aprendiz_de_token(token), self.ap)
        self.assertIsNone(svc.aprendiz_de_token(token + "x"))
        self.assertIsNone(svc.aprendiz_de_token("basura"))

    def test_qr_rapido_da_horas_una_sola_vez_y_se_deshace(self):
        c = self.cliente(self.u_personal)
        url = reverse("bienestar:actividad_qr_rapido", args=[self.act.id])
        token = svc.token_qr_de(self.ap)

        r = c.post(url, {"token": token}).json()
        self.assertEqual((r["ok"], r["estado"]), (True, "confirmado"))
        self.assertEqual(total_horas_de(self.ap), 2)

        r = c.post(url, {"token": token}).json()
        self.assertEqual(r["estado"], "ya_estaba")
        self.assertEqual(total_horas_de(self.ap), 2)
        self.assertEqual(HorasBienestar.objects.count(), 1)

        r = c.post(url, {"token": token, "accion": "deshacer"}).json()
        self.assertEqual(r["estado"], "deshecho")
        self.assertEqual(total_horas_de(self.ap), 0)

        # Volver a escanear después de deshacer sí vuelve a dar horas.
        r = c.post(url, {"token": token}).json()
        self.assertEqual(r["estado"], "confirmado")
        self.assertEqual(total_horas_de(self.ap), 2)

    def test_qr_rapido_rechaza_token_falso_y_actividad_cerrada(self):
        c = self.cliente(self.u_personal)
        url = reverse("bienestar:actividad_qr_rapido", args=[self.act.id])
        self.assertEqual(c.post(url, {"token": "falso"}).status_code, 404)
        self.act.estado = "cerrada"
        self.act.save()
        r = c.post(url, {"token": svc.token_qr_de(self.ap)})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(total_horas_de(self.ap), 0)

    def test_aprendiz_no_puede_darse_horas_con_su_propio_qr(self):
        url = reverse("bienestar:actividad_qr_rapido", args=[self.act.id])
        r = self.cliente(self.u_ap).post(url, {"token": svc.token_qr_de(self.ap)})
        self.assertIn(r.status_code, (302, 403))
        self.assertEqual(total_horas_de(self.ap), 0)

    def test_pagina_de_camara_normal(self):
        token = svc.token_qr_de(self.ap)
        url = reverse("bienestar:extracurricular_qr", args=[token])
        c = self.cliente(self.u_personal)
        self.assertContains(c.get(url), "Uniforme")
        c.post(url, {"actividad": self.act.id})
        self.assertEqual(total_horas_de(self.ap), 2)
        # Un aprendiz abriendo ese enlace no recibe nada.
        r = self.cliente(self.u_ap).post(url, {"actividad": self.act.id})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(HorasBienestar.objects.count(), 1)

    def test_imagen_qr_solo_aprendiz(self):
        url = reverse("bienestar:qr_extracurricular_imagen")
        r = self.cliente(self.u_ap).get(url)
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "image/png"))
        self.assertIn(r.status_code, (200,))
        self.assertEqual(self.cliente(self.u_personal).get(url).status_code, 403)


class ConteoUnificadoTests(Base):

    def _evento_con_horas(self, horas):
        ini = timezone.now() - timedelta(days=3)
        ev = Evento.objects.create(
            titulo="Yoga", lugar="X", horas_otorgadas=horas, creado_por=self.u_personal,
            fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2))
        ins = Inscripcion.objects.create(evento=ev, aprendiz=self.ap)
        from bienestar.services.asistencia import registrar_asistencia_y_horas
        registrar_asistencia_y_horas(inscripcion=ins, asistio=True, cantidad_horas=horas,
                                     motivo="x", asignado_por=self.personal)

    def test_suma_eventos_y_extracurriculares(self):
        self._evento_con_horas(4)
        svc.otorgar_horas(actividad=self.act, aprendiz=self.ap, horas=2,
                          asignado_por=self.personal, metodo="qr")
        self.assertEqual(total_horas_de(self.ap), 6)
        conceptos = sorted(h.concepto for h in horas_de(self.ap))
        self.assertEqual(conceptos, ["Uniforme (por mérito)", "Yoga"])
        self.assertEqual(total_horas_de(self.ap2), 0)

    def test_historial_pagina_y_panel(self):
        svc.otorgar_horas(actividad=self.act, aprendiz=self.ap, horas=2,
                          asignado_por=self.personal, metodo="qr")
        c = self.cliente(self.u_ap)
        self.assertContains(c.get(reverse("bienestar:mi_historial")), "Uniforme")
        self.assertContains(c.get(reverse("usuarios:dashboard_aprendiz")), "Uniforme (por mérito)")
        self.assertEqual(c.get(reverse("bienestar:mi_historial_exportar") + "?formato=excel").status_code, 200)
        fila = historial_extracurricular_de(self.ap)[0]
        self.assertEqual((fila.estado_codigo, fila.horas), ("otorgada", 2))

    def test_constancia_pdf_incluye_la_actividad(self):
        svc.otorgar_horas(actividad=self.act, aprendiz=self.ap, horas=2,
                          asignado_por=self.personal, metodo="qr")
        constancia = emitir_constancia(self.ap)
        self.assertEqual(constancia.total_horas, 2)
        pdf = generar_pdf_constancia(constancia, "http://x/verificar/")
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_restriccion_una_sola_fuente(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            HorasBienestar.objects.create(cantidad_horas=1, motivo="x", asignado_por=self.personal)


class PermisosTests(Base):

    def test_administrador_mira_pero_no_asigna(self):
        from usuarios.models import Administrador
        u = Usuario.objects.create_user(
            numero_documento="9", password="x", tipo_documento="CC",
            nombres="Adm", apellidos="P", email="9@x.co")
        Administrador.objects.create(usuario=u, fecha_ingreso=date(2026, 1, 1))
        c = self.cliente(u)
        p, _ = svc.unirse_con_codigo(self.ap, self.act.codigo)
        self.assertEqual(c.get(reverse("bienestar:actividad_detalle", args=[self.act.id])).status_code, 200)
        c.post(reverse("bienestar:actividad_detalle", args=[self.act.id]),
               {f"dar_{p.id}": "on", f"horas_{p.id}": "2"})
        self.assertEqual(total_horas_de(self.ap), 0)
        c.post(reverse("bienestar:actividad_crear"), {"titulo": "Nueva", "horas": 1, "fecha": "2026-10-01"})
        self.assertEqual(ActividadExtracurricular.objects.count(), 1)

    def test_crear_editar_cerrar_y_eliminar(self):
        c = self.cliente(self.u_personal)
        c.post(reverse("bienestar:actividad_crear"),
               {"titulo": "Charla", "descripcion": "x", "horas": 1, "fecha": "2026-10-01"})
        nueva = ActividadExtracurricular.objects.get(titulo="Charla")
        self.assertEqual(nueva.creado_por, self.personal)
        c.post(reverse("bienestar:actividad_estado", args=[nueva.id]))
        nueva.refresh_from_db()
        self.assertEqual(nueva.estado, "cerrada")
        c.post(reverse("bienestar:actividad_eliminar", args=[nueva.id]))
        self.assertFalse(ActividadExtracurricular.objects.filter(pk=nueva.pk).exists())

    def test_no_se_elimina_una_actividad_que_dio_horas(self):
        svc.otorgar_horas(actividad=self.act, aprendiz=self.ap, horas=2,
                          asignado_por=self.personal, metodo="qr")
        self.cliente(self.u_personal).post(reverse("bienestar:actividad_eliminar", args=[self.act.id]))
        self.assertTrue(ActividadExtracurricular.objects.filter(pk=self.act.pk).exists())

    def test_horas_fuera_de_rango_se_rechazan(self):
        c = self.cliente(self.u_personal)
        c.post(reverse("bienestar:actividad_crear"), {"titulo": "Mala", "horas": 0, "fecha": "2026-10-01"})
        c.post(reverse("bienestar:actividad_crear"), {"titulo": "Mala2", "horas": 99, "fecha": "2026-10-01"})
        self.assertEqual(ActividadExtracurricular.objects.count(), 1)
