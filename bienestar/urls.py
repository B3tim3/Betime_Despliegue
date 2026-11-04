from django.urls import path

from bienestar import views, views_extracurriculares as extra

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
    # Horas de bienestar por mérito (fuera de eventos)
    path("extracurriculares/recibir/", extra.recibir_extracurriculares, name="recibir_extracurriculares"),
    path("extracurriculares/mi-qr/imagen/", extra.qr_extracurricular_imagen, name="qr_extracurricular_imagen"),
    path("extracurriculares/qr/<str:token>/", extra.extracurricular_qr, name="extracurricular_qr"),
    path("extracurriculares/", extra.actividades_lista, name="actividades_lista"),
    path("extracurriculares/crear/", extra.actividad_crear, name="actividad_crear"),
    path("extracurriculares/<int:actividad_id>/", extra.actividad_detalle, name="actividad_detalle"),
    path("extracurriculares/<int:actividad_id>/editar/", extra.actividad_editar, name="actividad_editar"),
    path("extracurriculares/<int:actividad_id>/estado/", extra.actividad_estado, name="actividad_estado"),
    path("extracurriculares/<int:actividad_id>/eliminar/", extra.actividad_eliminar, name="actividad_eliminar"),
    path("extracurriculares/<int:actividad_id>/agregar/", extra.actividad_agregar, name="actividad_agregar"),
    path("extracurriculares/<int:actividad_id>/escanear/", extra.actividad_escanear, name="actividad_escanear"),
    path("extracurriculares/<int:actividad_id>/qr-rapido/", extra.actividad_qr_rapido, name="actividad_qr_rapido"),
]
