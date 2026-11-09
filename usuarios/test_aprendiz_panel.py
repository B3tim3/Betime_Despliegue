"""
Corrección de datos de un aprendiz por Bienestar (Panel -> Aprendices -> Editar),
centro de formación en los listados y resumen del inicio del panel.

Se ejecutan con:   python manage.py test usuarios.test_aprendiz_panel
"""

from datetime import date

from django.urls import reverse

from core.models import RegistroAuditoria
from notificaciones.models import Notificacion
from usuarios.models import Administrador, Aprendiz, PersonalBienestar, Usuario
from usuarios.services.datos_aprendiz import CENTRO_FORMACION, DatosAprendiz
from usuarios.test_perfil import PerfilBase


class EdicionBase(PerfilBase):

    def setUp(self):
        super().setUp()
        self.bienestar = Usuario.objects.create_user(
            numero_documento="900000002", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Paola", apellidos="Bienestar", email="paola@example.com")
        PersonalBienestar.objects.create(usuario=self.bienestar, cargo="Profesional", fecha_ingreso=date(2026, 1, 1))
        self.url_editar = reverse("usuarios:aprendices_editar", args=[self.aprendiz.pk])
        self.client.force_login(self.bienestar)

    def post(self, **cambios):
        datos = {
            "tipo_documento": "CC", "numero_documento": "1012345678", "nombres": "Juan",
            "apellidos": "Rodríguez", "genero": "M", "email": "juan@example.com",
            "telefono": "3001234567", "grupo": self.g_dia.id, "estado": "activo",
        }
        datos.update(cambios)
        return self.client.post(self.url_editar, datos)

    def recargar(self):
        self.aprendiz = Aprendiz.objects.select_related("usuario", "grupo").get(pk=self.aprendiz.pk)
        self.usuario = self.aprendiz.usuario


class CorregirDatosTests(EdicionBase):

    def test_la_pantalla_muestra_todos_los_campos(self):
        r = self.client.get(self.url_editar)
        self.assertEqual(r.status_code, 200)
        for campo in ("tipo_documento", "numero_documento", "nombres", "apellidos", "genero", "email", "telefono", "grupo", "estado"):
            self.assertContains(r, f'name="{campo}"')
        self.assertContains(r, CENTRO_FORMACION)
        self.assertContains(r, "1012345678")

    def test_corrige_nombre_y_documento(self):
        r = self.post(nombres="  Juan   Andrés ", numero_documento="1012345999", tipo_documento="TI")
        self.assertRedirects(r, reverse("usuarios:aprendices_lista"), fetch_redirect_response=False)
        self.recargar()
        self.assertEqual((self.usuario.nombres, self.usuario.numero_documento, self.usuario.tipo_documento),
                         ("Juan Andrés", "1012345999", "TI"))

    def test_con_el_documento_nuevo_puede_iniciar_sesion(self):
        self.post(numero_documento="1012345999")
        self.client.logout()
        self.assertTrue(self.client.login(numero_documento="1012345999", password="ClaveSegura#2026"))
        self.assertFalse(self.client.login(numero_documento="1012345678", password="ClaveSegura#2026"))

    def test_avisa_que_cambio_el_documento(self):
        r = self.client.post(self.url_editar, {
            "tipo_documento": "CC", "numero_documento": "1012345999", "nombres": "Juan", "apellidos": "Rodríguez",
            "genero": "M", "email": "juan@example.com", "telefono": "3001234567",
            "grupo": self.g_dia.id, "estado": "activo"}, follow=True)
        self.assertContains(r, "debe iniciar sesión con CC 1012345999")

    def test_documento_repetido_se_rechaza_y_no_cambia_nada(self):
        r = self.post(numero_documento="1099999999", nombres="Cambiado")
        self.assertEqual(r.status_code, 200)
        self.assertIn("numero_documento", r.context["form"].errors)
        self.recargar()
        self.assertEqual((self.usuario.numero_documento, self.usuario.nombres), ("1012345678", "Juan"))

    def test_correo_repetido_se_rechaza(self):
        r = self.post(email="OTRA@example.com")
        self.assertIn("email", r.context["form"].errors)

    def test_su_propio_documento_y_correo_no_cuentan_como_repetidos(self):
        r = self.post()   # sin cambios
        self.assertEqual(r.status_code, 302)

    def test_telefono_se_limpia_y_se_valida(self):
        self.post(telefono="300 123-4567")
        self.recargar()
        self.assertEqual(self.usuario.telefono, "3001234567")
        r = self.post(telefono="abc")
        self.assertIn("telefono", r.context["form"].errors)

    def test_correo_y_telefono_se_pueden_dejar_vacios_en_cuentas_antiguas(self):
        self.post(email="", telefono="", genero="")
        self.recargar()
        self.assertIsNone(self.usuario.email)
        self.assertEqual((self.usuario.telefono, self.usuario.genero), ("", ""))
        # Dos cuentas sin correo no chocan entre sí (el campo es único: queda NULL, no "")
        self.otro.email = None
        self.otro.save()
        self.post(email="")   # no debe fallar

    def test_cambia_grupo_y_estado(self):
        self.post(grupo=self.g_tec.id, estado="egresado")
        self.recargar()
        self.assertEqual((self.aprendiz.grupo, self.aprendiz.estado), (self.g_tec, "egresado"))

    def test_si_algo_falla_no_se_guarda_nada_a_medias(self):
        self.post(nombres="Nuevo Nombre", grupo=999999)   # grupo inexistente
        self.recargar()
        self.assertEqual(self.usuario.nombres, "Juan")

    def test_el_administrador_tambien_puede(self):
        admin = Usuario.objects.create_user(
            numero_documento="1", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Admin", apellidos="X", email="admin@example.com")
        Administrador.objects.create(usuario=admin, fecha_ingreso=date(2026, 1, 1))
        self.client.force_login(admin)
        self.assertEqual(self.post(nombres="Por Admin").status_code, 302)

    def test_un_aprendiz_no_puede_editar_a_otro(self):
        self.client.force_login(self.otro)
        self.post(nombres="Hackeado")
        self.recargar()
        self.assertEqual(self.usuario.nombres, "Juan")


class BitacoraYAvisoTests(EdicionBase):

    def test_auditoria_guarda_antes_y_despues_de_cada_dato(self):
        self.post(nombres="Juan Andrés", numero_documento="1012345999")
        r = RegistroAuditoria.objects.get(accion="aprendiz_editado")
        self.assertEqual(set(r.detalles), {"nombres", "numero_documento"})
        self.assertEqual(r.detalles["nombres"], {"antes": "Juan", "despues": "Juan Andrés"})
        self.assertEqual(r.usuario, self.bienestar)

    def test_sin_cambios_no_hay_bitacora_ni_aviso(self):
        self.post()
        self.assertFalse(RegistroAuditoria.objects.filter(accion="aprendiz_editado").exists())
        self.assertFalse(Notificacion.objects.filter(usuario=self.usuario).exists())

    def test_el_aprendiz_recibe_aviso_de_lo_corregido(self):
        self.post(apellidos="Rodríguez Pinzón", telefono="3009998888")
        n = Notificacion.objects.get(usuario=self.usuario)
        self.assertIn("apellidos", n.mensaje)
        self.assertIn("teléfono", n.mensaje)
        self.assertEqual(n.url, "/usuarios/perfil/")

    def test_cambiar_solo_el_estado_no_notifica(self):
        self.post(estado="retirado")
        self.assertFalse(Notificacion.objects.filter(usuario=self.usuario).exists())
        self.assertTrue(RegistroAuditoria.objects.filter(accion="aprendiz_editado").exists())


class CentroDeFormacionTests(EdicionBase):

    def test_esta_en_los_datos_del_aprendiz(self):
        datos = DatosAprendiz.de(self.aprendiz)
        self.assertEqual(datos.centro, "Centro de Diseño y Metrología (C.D.M)")
        self.assertIn("Centro de formación", DatosAprendiz.ENCABEZADOS)
        self.assertEqual(len(datos.como_fila()), len(DatosAprendiz.ENCABEZADOS))

    def test_aparece_en_el_perfil_del_aprendiz(self):
        self.client.force_login(self.usuario)
        r = self.client.get(reverse("usuarios:perfil"))
        self.assertContains(r, "Centro de formación")
        self.assertContains(r, CENTRO_FORMACION)

    def test_aparece_en_la_exportacion_de_aprendices(self):
        r = self.client.get(reverse("usuarios:aprendices_exportar"), {"formato": "excel"})
        self.assertEqual(r.status_code, 200)


class ListaYPanelTests(EdicionBase):

    def test_la_lista_muestra_contacto_y_buscar_por_correo(self):
        r = self.client.get(reverse("usuarios:aprendices_lista"))
        self.assertContains(r, "juan@example.com")
        self.assertContains(r, "CC 1012345678")
        r = self.client.get(reverse("usuarios:aprendices_lista"), {"q": "otra@example"})
        self.assertContains(r, "1099999999")
        self.assertNotContains(r, "1012345678")

    def test_inicio_de_bienestar_ya_no_dice_proximamente(self):
        r = self.client.get(reverse("usuarios:dashboard_bienestar"))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Próximamente")
        self.assertEqual(r.context["total_aprendices_activos"], 2)
        self.assertContains(r, "Aprendices activos")

    def test_inicio_del_administrador(self):
        admin = Usuario.objects.create_user(
            numero_documento="1", password="ClaveSegura#2026", tipo_documento="CC",
            nombres="Admin", apellidos="X", email="admin@example.com")
        Administrador.objects.create(usuario=admin, fecha_ingreso=date(2026, 1, 1))
        self.client.force_login(admin)
        r = self.client.get(reverse("usuarios:dashboard_admin"))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "próximas iteraciones")
