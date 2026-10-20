from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from usuarios import views
from usuarios.forms import RecuperarContrasenaForm, NuevaContrasenaForm

app_name = "usuarios"

urlpatterns = [
    path("registro/", views.registro_aprendiz, name="registro"),
    path("ajax/fichas/", views.fichas_por_programa, name="fichas_por_programa"),
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
    path("panel/programas/<int:programa_id>/fichas/", views.FichaListView.as_view(), name="fichas_de_programa"),

    # ---------- Panel: Jornadas (Administrador) ----------

    path("panel/jornadas/", views.JornadaListView.as_view(), name="jornadas_lista"),
    path("panel/jornadas/exportar/", views.exportar_jornadas, name="jornadas_exportar"),
    path("panel/jornadas/crear/", views.JornadaCreateView.as_view(), name="jornadas_crear"),
    path("panel/jornadas/<int:pk>/editar/", views.JornadaUpdateView.as_view(), name="jornadas_editar"),
    path("panel/jornadas/<int:pk>/eliminar/", views.JornadaDeleteView.as_view(), name="jornadas_eliminar"),
    path("panel/jornadas/<int:jornada_id>/fichas/", views.FichaListView.as_view(), name="fichas_de_jornada"),

    # ---------- Panel: Fichas (Bienestar / Administrador) ----------

    path("panel/fichas/", views.FichaListView.as_view(), name="fichas_lista"),
    path("panel/fichas/exportar/", views.exportar_fichas, name="fichas_exportar"),
    path("panel/fichas/crear/", views.FichaCreateView.as_view(), name="fichas_crear"),
    path("panel/fichas/<int:pk>/editar/", views.FichaUpdateView.as_view(), name="fichas_editar"),
    path("panel/fichas/<int:pk>/eliminar/", views.FichaDeleteView.as_view(), name="fichas_eliminar"),
    path("panel/fichas/<int:ficha_id>/aprendices/", views.AprendizListView.as_view(), name="aprendices_de_ficha"),

    # ---------- Panel: Aprendices (Bienestar / Administrador) ----------
    # Se crean por auto-registro; aquí solo se editan (ficha/estado).

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
