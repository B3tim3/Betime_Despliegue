from django.urls import path

from notificaciones import views

app_name = "notificaciones"

urlpatterns = [
    path("", views.lista_notificaciones, name="lista"),
    path("marcar-todas/", views.marcar_todas_leidas, name="marcar_todas"),
    path("recordatorios/ejecutar/", views.ejecutar_recordatorios, name="ejecutar_recordatorios"),
    path("<int:notificacion_id>/abrir/", views.abrir_notificacion, name="abrir"),
    path("<int:notificacion_id>/leida/", views.marcar_leida, name="marcar_leida"),
]
