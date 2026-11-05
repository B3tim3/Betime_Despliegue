from django.urls import path

from actividades import views

app_name = "actividades"

urlpatterns = [
    path("", views.lista_actividades, name="lista"),
    path("panel/", views.ActividadListView.as_view(), name="panel_lista"),
    path("panel/exportar/", views.exportar_actividades, name="panel_exportar"),
    path("panel/crear/", views.ActividadCreateView.as_view(), name="crear"),
    path("panel/<int:pk>/editar/", views.ActividadUpdateView.as_view(), name="editar"),
    path("panel/<int:pk>/eliminar/", views.ActividadDeleteView.as_view(), name="eliminar"),
    path("panel/<int:actividad_id>/inscritos/", views.checklist_inscritos, name="panel_inscritos"),
    path("panel/inscritos/exportar/", views.exportar_inscritos, name="panel_inscritos_exportar"),
    path("panel/escanear-qr/", views.escanear_qr, name="escanear_qr"),
    path("asistencia/confirmar/<uuid:token>/", views.confirmar_asistencia_qr, name="confirmar_asistencia_qr"),
    path("asistencia/confirmar/<uuid:token>/rapido/", views.confirmar_asistencia_qr_rapido, name="confirmar_qr_rapido"),
    path("<int:actividad_id>/", views.detalle_actividad, name="detalle"),
    path("<int:actividad_id>/inscribirse/", views.inscribirse_actividad, name="inscribirse"),
    path("mis-inscripciones/<int:inscripcion_id>/cancelar/", views.cancelar_inscripcion, name="cancelar_inscripcion"),
    path("mis-inscripciones/<int:inscripcion_id>/qr/", views.mi_qr_inscripcion, name="mi_qr"),
    path("mis-inscripciones/<int:inscripcion_id>/qr/imagen/", views.qr_imagen_inscripcion, name="qr_imagen"),
]
