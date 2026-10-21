from django.urls import path

from bienestar import views

app_name = "bienestar"

urlpatterns = [
    path("configuracion/", views.configuracion, name="configuracion"),
    path("mi-historial/", views.mi_historial, name="mi_historial"),
    path("mi-historial/exportar/", views.mi_historial_exportar, name="mi_historial_exportar"),
    path("constancia/", views.descargar_constancia, name="constancia"),
    path("constancia/verificar/<str:codigo>/", views.verificar_constancia, name="verificar_constancia"),
    path("nosotros/", views.nosotros, name="nosotros"),
    path("nosotros/panel/", views.panel_nosotros, name="panel_nosotros"),
    path("nosotros/panel/exportar/", views.exportar_miembros, name="panel_exportar"),
    path("nosotros/panel/crear/", views.crear_miembro, name="crear_miembro"),
    path("nosotros/panel/<int:miembro_id>/editar/", views.editar_miembro, name="editar_miembro"),
    path("nosotros/panel/<int:miembro_id>/eliminar/", views.eliminar_miembro, name="eliminar_miembro"),
]
