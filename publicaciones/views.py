from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.services.exportar import responder_export
from publicaciones.forms import PublicacionForm
from publicaciones.models import Publicacion
from usuarios.decorators import personal_bienestar_requerido
from usuarios.mixins import PersonalBienestarRequeridoMixin


def lista_publicaciones(request):

    publicaciones = Publicacion.objects.filter(
        estado="publicado"
    ).order_by("-fecha_publicacion")

    return render(request, "publicaciones/lista.html", {
        "publicaciones": publicaciones,
    })


def detalle_publicacion(request, publicacion_id):

    publicacion = get_object_or_404(
        Publicacion,
        id=publicacion_id,
        estado="publicado"
    )

    return render(request, "publicaciones/detalle.html", {
        "publicacion": publicacion,
    })


# ---------- Panel de gestión (Personal de Bienestar / Administrador) ----------
# CRUD como Class-Based Views, igual que ProgramaFormacion/Jornada/Ficha en usuarios.

class PublicacionListView(PersonalBienestarRequeridoMixin, ListView):
    model = Publicacion
    template_name = "publicaciones/panel_lista.html"
    context_object_name = "publicaciones"
    ordering = ["-fecha_creacion"]
    paginate_by = 15


class PublicacionCreateView(PersonalBienestarRequeridoMixin, CreateView):
    model = Publicacion
    form_class = PublicacionForm
    template_name = "publicaciones/form.html"
    success_url = reverse_lazy("publicaciones:panel_lista")
    extra_context = {"titulo_pagina": "Crear publicación"}

    def form_valid(self, form):
        form.instance.autor = self.request.user

        if form.instance.estado == "publicado" and not form.instance.fecha_publicacion:
            form.instance.fecha_publicacion = timezone.now()

        messages.success(self.request, "Publicación creada correctamente.")
        return super().form_valid(form)


class PublicacionUpdateView(PersonalBienestarRequeridoMixin, UpdateView):
    model = Publicacion
    form_class = PublicacionForm
    template_name = "publicaciones/form.html"
    success_url = reverse_lazy("publicaciones:panel_lista")
    extra_context = {"titulo_pagina": "Editar publicación"}

    def form_valid(self, form):
        if form.instance.estado == "publicado" and not form.instance.fecha_publicacion:
            form.instance.fecha_publicacion = timezone.now()

        messages.success(self.request, "Publicación actualizada correctamente.")
        return super().form_valid(form)


class PublicacionDeleteView(PersonalBienestarRequeridoMixin, DeleteView):
    model = Publicacion
    template_name = "publicaciones/confirmar_eliminar.html"
    context_object_name = "publicacion"
    success_url = reverse_lazy("publicaciones:panel_lista")

    def form_valid(self, form):
        messages.success(self.request, "Publicación eliminada.")
        return super().form_valid(form)


@personal_bienestar_requerido
def exportar_publicaciones(request):
    publicaciones = Publicacion.objects.order_by("-fecha_creacion")

    q = request.GET.get("q", "").strip()
    if q:
        publicaciones = publicaciones.filter(
            Q(titulo__icontains=q) |
            Q(autor__nombres__icontains=q) |
            Q(autor__apellidos__icontains=q)
        )

    estado = request.GET.get("estado", "").strip()
    if estado:
        publicaciones = publicaciones.filter(estado=estado)

    encabezados = ["Título", "Autor", "Estado", "Fecha publicación"]
    filas = [
        [p.titulo, p.autor.get_full_name(), p.estado, p.fecha_publicacion]
        for p in publicaciones
    ]

    return responder_export(request, "publicaciones", "Publicaciones", encabezados, filas, "publicaciones:panel_lista")
