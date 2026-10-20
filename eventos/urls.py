from django.urls import path

from eventos import views

app_name = "eventos"

urlpatterns = [
    path("", views.lista_eventos, name="lista"),
    path("panel/", views.EventoListView.as_view(), name="panel_lista"),
    path("panel/exportar/", views.exportar_eventos, name="panel_exportar"),
    path("panel/inscritos/exportar/", views.exportar_inscritos, name="panel_exportar_inscritos"),
    path("panel/crear/", views.EventoCreateView.as_view(), name="crear"),
    path("panel/<int:pk>/editar/", views.EventoUpdateView.as_view(), name="editar"),
    path("panel/<int:pk>/eliminar/", views.EventoDeleteView.as_view(), name="eliminar"),
    path("panel/<int:evento_id>/inscritos/", views.checklist_inscritos, name="panel_inscritos"),
    path("panel/escanear-qr/", views.escanear_qr, name="escanear_qr"),
    path("asistencia/confirmar/<uuid:token>/", views.confirmar_asistencia_qr, name="confirmar_asistencia_qr"),
    path("<int:evento_id>/", views.detalle_evento, name="detalle"),
    path("<int:evento_id>/inscribirse/", views.inscribirse_evento, name="inscribirse"),
    path("mis-inscripciones/<int:inscripcion_id>/qr/", views.mi_qr_inscripcion, name="mi_qr"),
    path("mis-inscripciones/<int:inscripcion_id>/qr/imagen/", views.qr_imagen_inscripcion, name="qr_imagen"),
]
