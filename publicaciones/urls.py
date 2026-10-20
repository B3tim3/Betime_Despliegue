from django.urls import path

from publicaciones import views

app_name = "publicaciones"

urlpatterns = [
    path("", views.lista_publicaciones, name="lista"),
    path("panel/", views.PublicacionListView.as_view(), name="panel_lista"),
    path("panel/exportar/", views.exportar_publicaciones, name="panel_exportar"),
    path("panel/crear/", views.PublicacionCreateView.as_view(), name="crear"),
    path("panel/<int:pk>/editar/", views.PublicacionUpdateView.as_view(), name="editar"),
    path("panel/<int:pk>/eliminar/", views.PublicacionDeleteView.as_view(), name="eliminar"),
    path("<int:publicacion_id>/", views.detalle_publicacion, name="detalle"),
]
