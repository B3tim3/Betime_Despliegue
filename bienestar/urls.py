from django.urls import path

from bienestar import views

app_name = "bienestar"

urlpatterns = [
    path("nosotros/", views.nosotros, name="nosotros"),
    path("nosotros/panel/", views.panel_nosotros, name="panel_nosotros"),
    path("nosotros/panel/exportar/", views.exportar_miembros, name="panel_exportar"),
    path("nosotros/panel/crear/", views.crear_miembro, name="crear_miembro"),
    path("nosotros/panel/<int:miembro_id>/editar/", views.editar_miembro, name="editar_miembro"),
    path("nosotros/panel/<int:miembro_id>/eliminar/", views.eliminar_miembro, name="eliminar_miembro"),
]
