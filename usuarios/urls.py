from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from usuarios import views
from usuarios.forms import RecuperarContrasenaForm, NuevaContrasenaForm

app_name = "usuarios"

urlpatterns = [
    path("registro/", views.registro_aprendiz, name="registro"),
    path("ajax/jornadas/", views.jornadas_por_programa, name="jornadas_por_programa"),
    path("ajax/grupos/", views.grupos_por_programa, name="grupos_por_programa"),
    path("login/", views.login_view, name="login"),
    path("acceso-personal/", views.login_view, name="login_personal"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/aprendiz/", views.dashboard_aprendiz, name="dashboard_aprendiz"),
    path("dashboard/bienestar/", views.dashboard_bienestar, name="dashboard_bienestar"),
    path("dashboard/admin/", views.dashboard_admin, name="dashboard_admin"),
    path("panel/usuarios/crear/", views.crear_usuario_admin, name="crear_usuario"),

    # ---------- Panel: Programas de Formación (Administrador) ----------

    path("panel/programas/", views.ProgramaFormacionListView.as_view(), name="programas_lista"),
    path("panel/programas/exportar/", views.exportar_programas, name="programas_exportar"),
    path("panel/programas/crear/", views.ProgramaFormacionCreateView.as_view(), name="programas_crear"),
    path("panel/programas/<int:pk>/editar/", views.ProgramaFormacionUpdateView.as_view(), name="programas_editar"),
    path("panel/programas/<int:pk>/eliminar/", views.ProgramaFormacionDeleteView.as_view(), name="programas_eliminar"),
    path("panel/programas/<int:programa_id>/grupos/", views.GrupoListView.as_view(), name="grupos_de_programa"),

    # ---------- Panel: Niveles de formación (Administrador) ----------

    path("panel/niveles/", views.NivelFormacionListView.as_view(), name="niveles_lista"),
    path("panel/niveles/exportar/", views.exportar_niveles, name="niveles_exportar"),
    path("panel/niveles/crear/", views.NivelFormacionCreateView.as_view(), name="niveles_crear"),
    path("panel/niveles/<int:pk>/editar/", views.NivelFormacionUpdateView.as_view(), name="niveles_editar"),
    path("panel/niveles/<int:pk>/eliminar/", views.NivelFormacionDeleteView.as_view(), name="niveles_eliminar"),

    # ---------- Panel: Jornadas (Administrador) ----------

    path("panel/jornadas/", views.JornadaListView.as_view(), name="jornadas_lista"),
    path("panel/jornadas/exportar/", views.exportar_jornadas, name="jornadas_exportar"),
    path("panel/jornadas/crear/", views.JornadaCreateView.as_view(), name="jornadas_crear"),
    path("panel/jornadas/<int:pk>/editar/", views.JornadaUpdateView.as_view(), name="jornadas_editar"),
    path("panel/jornadas/<int:pk>/eliminar/", views.JornadaDeleteView.as_view(), name="jornadas_eliminar"),
    path("panel/jornadas/<int:jornada_id>/grupos/", views.GrupoListView.as_view(), name="grupos_de_jornada"),

    # ---------- Panel: Grupos (Bienestar / Administrador) ----------

    path("panel/grupos/", views.GrupoListView.as_view(), name="grupos_lista"),
    path("panel/grupos/exportar/", views.exportar_grupos, name="grupos_exportar"),
    path("panel/grupos/crear/", views.GrupoCreateView.as_view(), name="grupos_crear"),
    path("panel/grupos/<int:pk>/editar/", views.GrupoUpdateView.as_view(), name="grupos_editar"),
    path("panel/grupos/<int:pk>/eliminar/", views.GrupoDeleteView.as_view(), name="grupos_eliminar"),
    path("panel/grupos/<int:grupo_id>/aprendices/", views.AprendizListView.as_view(), name="aprendices_de_grupo"),

    # ---------- Panel: Aprendices (Bienestar / Administrador) ----------
    # Se crean por auto-registro; aquí solo se editan (grupo/estado).

    path("panel/aprendices/", views.AprendizListView.as_view(), name="aprendices_lista"),
    path("panel/aprendices/exportar/", views.exportar_aprendices, name="aprendices_exportar"),
    path("panel/aprendices/<int:pk>/editar/", views.AprendizUpdateView.as_view(), name="aprendices_editar"),
    path("panel/aprendices/<int:pk>/eliminar/", views.AprendizDeleteView.as_view(), name="aprendices_eliminar"),

    # ---------- Restablecer contraseña ----------

    path(
        "recuperar-contrasena/",
        auth_views.PasswordResetView.as_view(
            form_class=RecuperarContrasenaForm,
            template_name="usuarios/password_reset.html",
            email_template_name="usuarios/password_reset_email.html",
            subject_template_name="usuarios/password_reset_subject.txt",
            success_url=reverse_lazy("usuarios:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "recuperar-contrasena/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="usuarios/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "recuperar-contrasena/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=NuevaContrasenaForm,
            template_name="usuarios/password_reset_confirm.html",
            success_url=reverse_lazy("usuarios:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "recuperar-contrasena/completado/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="usuarios/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
