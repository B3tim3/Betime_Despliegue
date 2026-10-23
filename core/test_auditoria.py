"""
Pruebas de la bitácora de auditoría (Paquete Seguridad 2).

Se ejecutan con:   python manage.py test core.test_auditoria
"""

from datetime import date, timedelta

from django.contrib import admin as django_admin
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from bienestar.models import ConfiguracionBienestar
from core.models import RegistroAuditoria
from core.services.auditoria import registrar
from eventos.models import Evento, Inscripcion
from usuarios.models import (
    Administrador, Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar,
    ProgramaFormacion, Usuario,
)
from usuarios.services.bloqueo import MAX_INTENTOS

CLAVE = "Clave-Segura-1"


class Base(TestCase):

    @classmethod
    def setUpTestData(cls):
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        cls.jornada = Jornada.objects.create(nombre="Diurna")
        cls.programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
        cls.g1 = Grupo.objects.create(
            numero_grupo="3000001", programa_formacion=cls.programa, jornada=cls.jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))
        cls.g2 = Grupo.objects.create(
            numero_grupo="3000002", programa_formacion=cls.programa, jornada=cls.jornada,
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
        cls.aprendiz = Aprendiz.objects.create(usuario=cls.u_ap, grupo=cls.g1, fecha_ingreso=date(2026, 1, 1))
        ini = timezone.now() + timedelta(days=3)
        cls.evento = Evento.objects.create(
            titulo="Yoga", lugar="Coliseo", horas_otorgadas=2, creado_por=cls.u_personal,
            fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2), estado="programado")
        cls.inscripcion = Inscripcion.objects.create(evento=cls.evento, aprendiz=cls.aprendiz)

    def entrar(self, usuario):
        self.client.force_login(usuario)

    def acciones(self, accion):
        return RegistroAuditoria.objects.filter(accion=accion)


class ServicioTests(Base):

    def test_registra_quien_y_desde_donde(self):
        pedido = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1")
        pedido.user = self.u_admin
        r = registrar("meta_horas", "algo", request=pedido, detalles={"a": 1})
        self.assertEqual(r.usuario, self.u_admin)
        self.assertIn("1", r.usuario_texto)
        self.assertEqual(r.ip, "203.0.113.7")
        self.assertEqual(r.detalles, {"a": 1})

    def test_sin_sesion_el_usuario_queda_vacio(self):
        r = registrar("login_bloqueado", "x")
        self.assertIsNone(r.usuario)
        self.assertEqual(r.usuario_texto, "")

    def test_un_registro_no_se_puede_modificar(self):
        r = registrar("meta_horas", "original")
        r.descripcion = "alterado"
        with self.assertRaises(ValueError):
            r.save()
        r.refresh_from_db()
        self.assertEqual(r.descripcion, "original")

    def test_el_admin_de_django_es_solo_lectura(self):
        modelo = django_admin.site._registry[RegistroAuditoria]
        pedido = RequestFactory().get("/")
        pedido.user = self.u_admin
        self.assertFalse(modelo.has_add_permission(pedido))
        self.assertFalse(modelo.has_change_permission(pedido))
        self.assertFalse(modelo.has_delete_permission(pedido))

    def test_si_la_cuenta_se_borra_el_registro_se_conserva(self):
        extra = Usuario.objects.create_user(
            numero_documento="77", password=CLAVE, tipo_documento="CC",
            nombres="Borrable", apellidos="X", email="b@x.co")
        r = registrar("meta_horas", "x", usuario=extra)
        extra.delete()
        r.refresh_from_db()
        self.assertIsNone(r.usuario)
        self.assertIn("Borrable", r.usuario_texto)


class AccionesAuditadasTests(Base):

    def test_editar_aprendiz_guarda_antes_y_despues(self):
        self.entrar(self.u_personal)
        self.client.post(reverse("usuarios:aprendices_editar", args=[self.aprendiz.pk]),
                         {"grupo": self.g2.pk, "estado": "retirado"})
        r = self.acciones("aprendiz_editado").get()
        self.assertEqual(r.usuario, self.u_personal)
        self.assertEqual(set(r.detalles), {"grupo", "estado"})
        self.assertEqual(r.detalles["estado"], {"antes": "activo", "despues": "retirado"})
        self.assertIn("3000001", r.detalles["grupo"]["antes"])
        self.assertIn("3000002", r.detalles["grupo"]["despues"])

    def test_editar_sin_cambios_no_registra(self):
        self.entrar(self.u_personal)
        self.client.post(reverse("usuarios:aprendices_editar", args=[self.aprendiz.pk]),
                         {"grupo": self.g1.pk, "estado": "activo"})
        self.assertFalse(self.acciones("aprendiz_editado").exists())

    def test_eliminar_aprendiz(self):
        self.entrar(self.u_personal)
        self.client.post(reverse("usuarios:aprendices_eliminar", args=[self.aprendiz.pk]))
        r = self.acciones("aprendiz_eliminado").get()
        self.assertIn("Aprendiz Prueba", r.descripcion)
        self.assertIn("3", r.descripcion)

    def test_abrir_a_mano_la_url_de_eliminar_aprendiz_ya_no_da_error(self):
        self.entrar(self.u_personal)
        r = self.client.get(reverse("usuarios:aprendices_eliminar", args=[self.aprendiz.pk]))
        self.assertRedirects(r, reverse("usuarios:aprendices_lista"))
        self.assertTrue(Aprendiz.objects.filter(pk=self.aprendiz.pk).exists())

    def test_cambio_de_meta_de_horas(self):
        ConfiguracionBienestar.obtener()
        self.entrar(self.u_admin)
        url = reverse("bienestar:configuracion")
        self.client.post(url, {"meta_horas": 60})
        r = self.acciones("meta_horas").get()
        self.assertEqual(r.detalles, {"antes": 40, "despues": 60})
        self.client.post(url, {"meta_horas": 60})  # mismo valor: nada nuevo
        self.assertEqual(self.acciones("meta_horas").count(), 1)

    def test_crear_cuenta_no_guarda_la_contrasena(self):
        self.entrar(self.u_admin)
        r = self.client.post(reverse("usuarios:crear_usuario"), {
            "tipo_perfil": "bienestar", "tipo_documento": "CC", "numero_documento": "555",
            "nombres": "Nueva", "apellidos": "Persona", "email": "n@x.co",
            "cargo": "Psicóloga", "password": "Secreta-Muy-Larga-9", "password_confirm": "Secreta-Muy-Larga-9",
        })
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        reg = self.acciones("usuario_creado").get()
        self.assertEqual(reg.usuario, self.u_admin)
        self.assertNotIn("Secreta", reg.descripcion + str(reg.detalles))

    def test_asistencia_por_checklist_solo_registra_cambios(self):
        self.entrar(self.u_personal)
        url = reverse("eventos:panel_inscritos", args=[self.evento.pk])
        datos = {f"asistio_{self.inscripcion.pk}": "on", f"horas_{self.inscripcion.pk}": "2"}
        self.client.post(url, datos)
        self.assertEqual(self.acciones("asistencia").count(), 1)
        self.client.post(url, datos)   # guardar de nuevo lo mismo
        self.assertEqual(self.acciones("asistencia").count(), 1)
        self.client.post(url, {f"asistio_{self.inscripcion.pk}": "on", f"horas_{self.inscripcion.pk}": "3"})
        self.assertEqual(self.acciones("asistencia").count(), 2)
        ultimo = self.acciones("asistencia").first()
        self.assertEqual((ultimo.detalles["horas_antes"], ultimo.detalles["horas_ahora"]), (2, 3))
        self.assertEqual(ultimo.detalles["metodo"], "checklist")
        self.assertEqual(ultimo.usuario, self.u_personal)

    def test_asistencia_por_qr_queda_marcada_como_qr(self):
        self.entrar(self.u_personal)
        self.client.post(reverse("eventos:confirmar_asistencia_qr", args=[self.inscripcion.token]))
        r = self.acciones("asistencia").get()
        self.assertEqual(r.detalles["metodo"], "QR")

    def test_cancelar_y_eliminar_evento(self):
        self.entrar(self.u_personal)
        datos = {
            "titulo": "Yoga", "descripcion": "", "lugar": "Coliseo", "horas_otorgadas": 2,
            "fecha_inicio": timezone.localtime(self.evento.fecha_inicio).strftime("%Y-%m-%d %H:%M"),
            "fecha_fin": timezone.localtime(self.evento.fecha_fin).strftime("%Y-%m-%d %H:%M"),
            "estado": "cancelado",
        }
        self.client.post(reverse("eventos:editar", args=[self.evento.pk]), datos)
        self.assertEqual(self.acciones("evento_cancelado").count(), 1)
        self.client.post(reverse("eventos:eliminar", args=[self.evento.pk]))
        r = self.acciones("evento_eliminado").get()
        self.assertIn("Yoga", r.descripcion)
        self.assertIn("1 inscripciones", r.descripcion)

    def test_eliminar_de_catalogo(self):
        extra = Jornada.objects.create(nombre="Mixta")
        self.entrar(self.u_admin)
        self.client.post(reverse("usuarios:jornadas_eliminar", args=[extra.pk]))
        self.assertIn("Mixta", self.acciones("catalogo_eliminado").get().descripcion)

    def test_eliminar_protegido_no_registra(self):
        self.entrar(self.u_admin)
        self.client.post(reverse("usuarios:jornadas_eliminar", args=[self.jornada.pk]))  # tiene grupos
        self.assertFalse(self.acciones("catalogo_eliminado").exists())

    def test_cambio_de_contrasena_propia(self):
        self.entrar(self.u_ap)
        self.client.post(reverse("usuarios:cambiar_contrasena"), {
            "old_password": CLAVE, "new_password1": "Otra-Clave-Muy-Larga-7", "new_password2": "Otra-Clave-Muy-Larga-7"})
        r = self.acciones("contrasena_cambiada").get()
        self.assertEqual(r.usuario, self.u_ap)
        self.assertNotIn("Otra-Clave", r.descripcion + str(r.detalles))

    def test_login_bloqueado_se_registra_una_sola_vez(self):
        for _ in range(MAX_INTENTOS + 3):
            self.client.post(reverse("usuarios:login"), {
                "tipo_documento": "CC", "numero_documento": "3", "password": "mala"})
        r = self.acciones("login_bloqueado").get()
        self.assertEqual(r.detalles["documento"], "3")
        self.assertIsNone(r.usuario)


class PaginaAuditoriaTests(Base):

    def setUp(self):
        registrar("meta_horas", "Cambio de meta de 40 a 60", usuario=self.u_admin)
        registrar("evento_eliminado", "Se eliminó el evento «Yoga»", usuario=self.u_personal)
        registrar("evento_eliminado", "<script>alert(1)</script>", usuario=self.u_personal)

    def test_el_administrador_la_ve(self):
        self.entrar(self.u_admin)
        r = self.client.get(reverse("auditoria"))
        self.assertContains(r, "Cambio de meta de 40 a 60")
        self.assertContains(r, "Se eliminó el evento")

    def test_el_personal_de_bienestar_no_entra(self):
        self.entrar(self.u_personal)
        r = self.client.get(reverse("auditoria"))
        self.assertEqual(r.status_code, 302)

    def test_filtra_por_accion_y_texto(self):
        self.entrar(self.u_admin)
        r = self.client.get(reverse("auditoria") + "?accion=meta_horas")
        self.assertContains(r, "Cambio de meta")
        self.assertNotContains(r, "Se eliminó el evento")
        r = self.client.get(reverse("auditoria") + "?q=Yoga")
        self.assertContains(r, "Se eliminó el evento")
        self.assertNotContains(r, "Cambio de meta")

    def test_accion_inventada_se_ignora(self):
        self.entrar(self.u_admin)
        r = self.client.get(reverse("auditoria") + "?accion=algo-raro")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Cambio de meta")

    def test_el_texto_se_escapa(self):
        self.entrar(self.u_admin)
        r = self.client.get(reverse("auditoria"))
        self.assertNotContains(r, "<script>alert(1)</script>")

    def test_paginacion(self):
        for i in range(40):
            registrar("meta_horas", f"registro {i}", usuario=self.u_admin)
        self.entrar(self.u_admin)
        r = self.client.get(reverse("auditoria"))
        self.assertEqual(len(r.context["pagina"].object_list), 30)
        r = self.client.get(reverse("auditoria") + "?page=2")
        self.assertEqual(r.status_code, 200)
