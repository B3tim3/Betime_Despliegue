"""
Prueba de permisos de TODAS las URLs de la aplicación.

Recorre automáticamente cada ruta, la visita como visitante, aprendiz,
Personal de Bienestar y Administrador, y comprueba que cada rol solo entra
adonde debe. Además, intenta enviar peticiones POST (borrar, editar...) con
los roles que NO tienen permiso y verifica que no se cambió nada en la base
de datos.

Si alguien agrega una URL nueva y no la anota en NIVELES, esta prueba FALLA
a propósito: obliga a decidir quién puede entrar antes de que la ruta quede
publicada por olvido.

Se ejecuta con:   python manage.py test core.test_permisos
"""

import re
from datetime import date, timedelta

from django.test import TestCase
from django.urls import get_resolver
from django.utils import timezone

from bienestar.models import ConstanciaHoras, MiembroBienestar
from eventos.models import Asistencia, Evento, Inscripcion
from notificaciones.models import Notificacion
from publicaciones.models import Publicacion
from usuarios.models import (
    Administrador, Aprendiz, Grupo, Jornada, NivelFormacion, PersonalBienestar,
    ProgramaFormacion, Usuario,
)

CLAVE = "x"

# ---------- Quién puede entrar a cada ruta ----------
PUBLICA = "publica"          # cualquiera, con o sin sesión
LOGUEADO = "logueado"        # cualquier persona con sesión iniciada
APRENDIZ = "aprendiz"        # solo aprendices
PERSONAL = "personal"        # Personal de Bienestar y Administrador
ADMIN = "admin"              # solo Administrador

PERMITIDOS = {
    PUBLICA: {"anon", "aprendiz", "personal", "admin"},
    LOGUEADO: {"aprendiz", "personal", "admin"},
    APRENDIZ: {"aprendiz"},
    PERSONAL: {"personal", "admin"},
    ADMIN: {"admin"},
}

NIVELES = {
    # --- núcleo público ---
    "": PUBLICA,
    "usuarios/registro/": PUBLICA,
    "usuarios/ajax/jornadas/": PUBLICA,
    "usuarios/ajax/grupos/": PUBLICA,
    "usuarios/login/": PUBLICA,
    "usuarios/acceso-personal/": PUBLICA,
    "usuarios/logout/": PUBLICA,
    "usuarios/recuperar-contrasena/": PUBLICA,
    "usuarios/recuperar-contrasena/enviado/": PUBLICA,
    "usuarios/recuperar-contrasena/confirmar/<uidb64>/<token>/": PUBLICA,
    "usuarios/recuperar-contrasena/completado/": PUBLICA,
    "publicaciones/": PUBLICA,
    "publicaciones/<int:publicacion_id>/": PUBLICA,
    "eventos/": PUBLICA,
    "eventos/<int:evento_id>/": PUBLICA,
    "bienestar/nosotros/": PUBLICA,
    "bienestar/constancia/verificar/<str:codigo>/": PUBLICA,
    "notificaciones/recordatorios/ejecutar/": PUBLICA,   # protegida por token (ver test aparte)
    # --- cualquier persona con sesión ---
    "usuarios/perfil/contrasena/": LOGUEADO,
    "usuarios/dashboard/": LOGUEADO,
    "eventos/asistencia/confirmar/<uuid:token>/": LOGUEADO,
    "eventos/asistencia/confirmar/<uuid:token>/rapido/": PERSONAL,
    "notificaciones/": LOGUEADO,
    "notificaciones/marcar-todas/": LOGUEADO,
    "notificaciones/<int:notificacion_id>/abrir/": LOGUEADO,
    "notificaciones/<int:notificacion_id>/leida/": LOGUEADO,
    # --- solo aprendices ---
    "usuarios/perfil/": APRENDIZ,
    "usuarios/dashboard/aprendiz/": APRENDIZ,
    "eventos/<int:evento_id>/inscribirse/": APRENDIZ,
    "eventos/mis-inscripciones/<int:inscripcion_id>/cancelar/": APRENDIZ,
    "eventos/mis-inscripciones/<int:inscripcion_id>/qr/": APRENDIZ,
    "eventos/mis-inscripciones/<int:inscripcion_id>/qr/imagen/": APRENDIZ,
    "bienestar/mi-historial/": APRENDIZ,
    "bienestar/mi-historial/exportar/": APRENDIZ,
    "bienestar/constancia/": APRENDIZ,
    # --- Personal de Bienestar y Administrador ---
    "usuarios/dashboard/bienestar/": PERSONAL,
    "usuarios/panel/grupos/": PERSONAL,
    "usuarios/panel/grupos/exportar/": PERSONAL,
    "usuarios/panel/grupos/crear/": PERSONAL,
    "usuarios/panel/grupos/<int:pk>/editar/": PERSONAL,
    "usuarios/panel/grupos/<int:pk>/eliminar/": PERSONAL,
    "usuarios/panel/grupos/<int:grupo_id>/aprendices/": PERSONAL,
    "usuarios/panel/programas/<int:programa_id>/grupos/": PERSONAL,
    "usuarios/panel/jornadas/<int:jornada_id>/grupos/": PERSONAL,
    "usuarios/panel/aprendices/": PERSONAL,
    "usuarios/panel/aprendices/exportar/": PERSONAL,
    "usuarios/panel/aprendices/<int:pk>/editar/": PERSONAL,
    "usuarios/panel/aprendices/<int:pk>/eliminar/": PERSONAL,
    "publicaciones/panel/": PERSONAL,
    "publicaciones/panel/exportar/": PERSONAL,
    "publicaciones/panel/crear/": PERSONAL,
    "publicaciones/panel/<int:pk>/editar/": PERSONAL,
    "publicaciones/panel/<int:pk>/eliminar/": PERSONAL,
    "eventos/panel/": PERSONAL,
    "eventos/panel/exportar/": PERSONAL,
    "eventos/panel/crear/": PERSONAL,
    "eventos/panel/<int:pk>/editar/": PERSONAL,
    "eventos/panel/<int:pk>/eliminar/": PERSONAL,
    "eventos/panel/<int:evento_id>/inscritos/": PERSONAL,
    "eventos/panel/inscritos/exportar/": PERSONAL,
    "eventos/panel/escanear-qr/": PERSONAL,
    "bienestar/nosotros/panel/": PERSONAL,
    "bienestar/nosotros/panel/exportar/": PERSONAL,
    "bienestar/nosotros/panel/crear/": PERSONAL,
    "bienestar/nosotros/panel/<int:miembro_id>/editar/": PERSONAL,
    "bienestar/nosotros/panel/<int:miembro_id>/eliminar/": PERSONAL,
    # --- solo Administrador ---
    "usuarios/dashboard/admin/": ADMIN,
    "usuarios/panel/usuarios/crear/": ADMIN,
    "usuarios/panel/programas/": ADMIN,
    "usuarios/panel/programas/exportar/": ADMIN,
    "usuarios/panel/programas/crear/": ADMIN,
    "usuarios/panel/programas/<int:pk>/editar/": ADMIN,
    "usuarios/panel/programas/<int:pk>/eliminar/": ADMIN,
    "usuarios/panel/niveles/": ADMIN,
    "usuarios/panel/niveles/exportar/": ADMIN,
    "usuarios/panel/niveles/crear/": ADMIN,
    "usuarios/panel/niveles/<int:pk>/editar/": ADMIN,
    "usuarios/panel/niveles/<int:pk>/eliminar/": ADMIN,
    "usuarios/panel/jornadas/": ADMIN,
    "usuarios/panel/jornadas/exportar/": ADMIN,
    "usuarios/panel/jornadas/crear/": ADMIN,
    "usuarios/panel/jornadas/<int:pk>/editar/": ADMIN,
    "usuarios/panel/jornadas/<int:pk>/eliminar/": ADMIN,
    "bienestar/configuracion/": ADMIN,
    "auditoria/": ADMIN,
}

# Rutas que solo aceptan POST (con GET responden 405 a todos: no se puede
# juzgar el permiso por GET, así que se juzga solo por POST).
SOLO_POST = {
    "usuarios/logout/",
    "eventos/mis-inscripciones/<int:inscripcion_id>/cancelar/",
    "eventos/asistencia/confirmar/<uuid:token>/rapido/",
    "notificaciones/marcar-todas/",
    "notificaciones/<int:notificacion_id>/leida/",
}

# Rutas públicas cuyo POST es legítimo (formularios abiertos) o que no
# modifican nada: no se ensayan con POST.
SIN_POST = {
    "", "usuarios/registro/", "usuarios/ajax/jornadas/", "usuarios/ajax/grupos/",
    "usuarios/login/", "usuarios/acceso-personal/", "usuarios/logout/",
    "usuarios/recuperar-contrasena/", "usuarios/recuperar-contrasena/enviado/",
    "usuarios/recuperar-contrasena/confirmar/<uidb64>/<token>/",
    "usuarios/recuperar-contrasena/completado/",
    "publicaciones/", "publicaciones/<int:publicacion_id>/", "eventos/",
    "eventos/<int:evento_id>/", "bienestar/nosotros/",
    "bienestar/constancia/verificar/<str:codigo>/",
    "notificaciones/recordatorios/ejecutar/",
}

PARAMETRO = re.compile(r"<(?:(\w+):)?(\w+)>")


def rutas():
    """Todas las rutas de la aplicación (sin /admin/ ni /media/), como texto."""
    def recorrer(patrones, prefijo=""):
        for p in patrones:
            texto = prefijo + str(p.pattern)
            if hasattr(p, "url_patterns"):
                yield from recorrer(p.url_patterns, texto)
            else:
                yield texto
    return sorted(
        r for r in recorrer(get_resolver().url_patterns)
        if not r.startswith("admin/") and not r.startswith("^media")
    )


class PermisosTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        nivel, _ = NivelFormacion.objects.get_or_create(nombre="Tecnólogo")
        cls.nivel = nivel
        cls.jornada = Jornada.objects.create(nombre="Diurna")
        cls.programa = ProgramaFormacion.objects.create(
            nombre="ADSO", codigo="P1", nivel_formacion=nivel, duracion_meses=24)
        cls.grupo = Grupo.objects.create(
            numero_grupo="3000001", programa_formacion=cls.programa, jornada=cls.jornada,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))

        def usuario(doc, nombre):
            return Usuario.objects.create_user(
                numero_documento=doc, password=CLAVE, tipo_documento="CC",
                nombres=nombre, apellidos="Prueba", email=f"{doc}@x.co")

        cls.u_admin = usuario("1", "Admin")
        Administrador.objects.create(usuario=cls.u_admin, fecha_ingreso=date(2026, 1, 1))
        cls.u_personal = usuario("2", "Personal")
        PersonalBienestar.objects.create(usuario=cls.u_personal, cargo="C", fecha_ingreso=date(2026, 1, 1))
        cls.u_ap = usuario("3", "Aprendiz")
        cls.aprendiz = Aprendiz.objects.create(usuario=cls.u_ap, grupo=cls.grupo, fecha_ingreso=date(2026, 1, 1))
        cls.u_otro = usuario("4", "Otro")
        cls.otro = Aprendiz.objects.create(usuario=cls.u_otro, grupo=cls.grupo, fecha_ingreso=date(2026, 1, 1))

        ini = timezone.now() + timedelta(days=3)
        cls.evento = Evento.objects.create(
            titulo="Yoga", lugar="Coliseo", horas_otorgadas=2, creado_por=cls.u_personal,
            fecha_inicio=ini, fecha_fin=ini + timedelta(hours=2), estado="programado")
        cls.inscripcion = Inscripcion.objects.create(evento=cls.evento, aprendiz=cls.aprendiz)
        cls.publicacion = Publicacion.objects.create(autor=cls.u_personal, titulo="Hola", contenido="x")
        cls.miembro = MiembroBienestar.objects.create(nombre="Ana", cargo="Psicóloga")
        cls.notificacion = Notificacion.objects.create(usuario=cls.u_ap, titulo="t", mensaje="m")
        cls.constancia = ConstanciaHoras.objects.create(
            aprendiz=cls.aprendiz, nombre="Aprendiz Prueba", tipo_documento="CC",
            numero_documento="3", programa="ADSO", grupo="3000001", total_horas=40, meta_horas=40)

    # ---------- utilidades ----------

    def valor(self, ruta, nombre):
        """Valor real para cada parámetro de la URL, para que ningún 404 oculte un permiso mal puesto."""
        if nombre == "pk":
            for clave, objeto in (
                ("programas", self.programa), ("niveles", self.nivel), ("jornadas", self.jornada),
                ("grupos", self.grupo), ("aprendices", self.aprendiz),
                ("publicaciones", self.publicacion), ("eventos", self.evento),
            ):
                if clave in ruta:
                    return objeto.pk
        return {
            "programa_id": self.programa.pk, "jornada_id": self.jornada.pk, "grupo_id": self.grupo.pk,
            "evento_id": self.evento.pk, "publicacion_id": self.publicacion.pk,
            "miembro_id": self.miembro.pk, "inscripcion_id": self.inscripcion.pk,
            "notificacion_id": self.notificacion.pk, "token": self.inscripcion.token,
            "codigo": self.constancia.codigo, "uidb64": "MQ", "pk": 1,
        }[nombre]

    def url(self, ruta):
        return "/" + PARAMETRO.sub(lambda m: str(self.valor(ruta, m.group(2))), ruta)

    def cliente(self, rol):
        from django.test import Client
        c = Client()
        usuarios = {"admin": self.u_admin, "personal": self.u_personal, "aprendiz": self.u_ap, "otro": self.u_otro}
        if rol in usuarios:
            c.force_login(usuarios[rol])  # sin calcular el hash de la contraseña: mucho más rápido
        return c

    def conteos(self):
        modelos = (Evento, Inscripcion, Grupo, ProgramaFormacion, Jornada, NivelFormacion,
                   Publicacion, MiembroBienestar, Aprendiz, Usuario, Notificacion, Asistencia)
        return {m.__name__: m.objects.count() for m in modelos}

    # ---------- las pruebas ----------

    def test_todas_las_rutas_estan_clasificadas(self):
        sin_clasificar = [r for r in rutas() if r not in NIVELES]
        self.assertEqual(
            sin_clasificar, [],
            "Rutas nuevas sin decidir quién puede entrar. Agrégalas a NIVELES en core/test_permisos.py: "
            f"{sin_clasificar}",
        )

    def test_no_quedan_rutas_clasificadas_que_ya_no_existen(self):
        sobrantes = [r for r in NIVELES if r not in set(rutas())]
        self.assertEqual(sobrantes, [], f"Rutas anotadas que ya no existen: {sobrantes}")

    def test_cada_rol_entra_solo_adonde_debe(self):
        fallos = []
        for ruta in rutas():
            nivel = NIVELES[ruta]
            url = self.url(ruta)
            for rol in ("anon", "aprendiz", "personal", "admin"):
                if ruta in SOLO_POST:
                    continue
                r = self.cliente(rol).get(url)
                destino = r.headers.get("Location", "")
                a_login = r.status_code == 302 and ("/login/" in destino or "/acceso-personal/" in destino)

                if rol in PERMITIDOS[nivel]:
                    if r.status_code == 403 or a_login:
                        fallos.append(f"{rol} NO pudo entrar a /{ruta} (debería): {r.status_code} {destino}")
                else:
                    if r.status_code not in (302, 403):
                        fallos.append(f"{rol} PUDO ver /{ruta} (no debería): {r.status_code}")
                    if rol == "anon" and nivel != PUBLICA and not a_login:
                        fallos.append(f"anon en /{ruta} no fue enviado al login: {r.status_code} {destino}")
        self.assertEqual(fallos, [], "\n".join(fallos))

    def test_los_roles_sin_permiso_no_cambian_nada_con_post(self):
        """POST (borrar, crear, editar...) de quien no tiene permiso: rechazado y sin tocar la base de datos."""
        fallos = []
        for ruta in rutas():
            if ruta in SIN_POST:
                continue
            nivel = NIVELES[ruta]
            url = self.url(ruta)
            for rol in ("anon", "aprendiz", "personal", "admin"):
                if rol in PERMITIDOS[nivel]:
                    continue
                antes = self.conteos()
                r = self.cliente(rol).post(url, {})
                if r.status_code not in (302, 403):
                    fallos.append(f"POST de {rol} a /{ruta}: respondió {r.status_code} (debería 302 o 403)")
                if self.conteos() != antes:
                    fallos.append(f"POST de {rol} a /{ruta} CAMBIÓ datos: {antes} -> {self.conteos()}")
        self.assertEqual(fallos, [], "\n".join(fallos))

    # ---------- reglas de pertenencia (entre personas del mismo rol) ----------

    def test_un_aprendiz_no_ve_el_qr_de_otro(self):
        c = self.cliente("otro")
        self.assertEqual(c.get(f"/eventos/mis-inscripciones/{self.inscripcion.pk}/qr/imagen/").status_code, 403)
        self.assertEqual(c.get(f"/eventos/mis-inscripciones/{self.inscripcion.pk}/qr/").status_code, 302)

    def test_un_aprendiz_no_cancela_la_inscripcion_de_otro(self):
        r = self.cliente("otro").post(f"/eventos/mis-inscripciones/{self.inscripcion.pk}/cancelar/")
        self.assertEqual(r.status_code, 404)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado, "inscrito")

    def test_un_aprendiz_no_abre_ni_marca_notificaciones_de_otro(self):
        c = self.cliente("otro")
        self.assertEqual(c.get(f"/notificaciones/{self.notificacion.pk}/abrir/").status_code, 404)
        c.post(f"/notificaciones/{self.notificacion.pk}/leida/")
        self.notificacion.refresh_from_db()
        self.assertFalse(self.notificacion.leida)

    def test_aprendiz_no_puede_confirmar_asistencia_por_qr(self):
        """Ver la pantalla del QR no basta: solo Personal de Bienestar registra la asistencia."""
        antes = Asistencia.objects.count()
        self.cliente("aprendiz").post(f"/eventos/asistencia/confirmar/{self.inscripcion.token}/")
        self.cliente("admin").post(f"/eventos/asistencia/confirmar/{self.inscripcion.token}/")
        self.assertEqual(Asistencia.objects.count(), antes)

    def test_publicacion_en_borrador_no_es_publica(self):
        self.assertEqual(self.publicacion.estado, "borrador")
        r = self.cliente("anon").get(f"/publicaciones/{self.publicacion.pk}/")
        self.assertNotEqual(r.status_code, 200)
        self.assertNotContains(self.cliente("anon").get("/publicaciones/"), "Hola")

    def test_endpoint_de_recordatorios_cerrado_sin_token(self):
        import os
        os.environ.pop("RECORDATORIOS_TOKEN", None)
        self.assertEqual(self.cliente("anon").get("/notificaciones/recordatorios/ejecutar/").status_code, 404)
