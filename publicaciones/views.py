from django.contrib import messages
from django.core.paginator import Paginator
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


def _minutos_lectura(texto):
    """Tiempo estimado de lectura: unas 200 palabras por minuto, mínimo 1."""
    return max(1, round(len(texto.split()) / 200))


def lista_publicaciones(request):
    """
    Lista pública: la más reciente va destacada (solo en la primera página y
    sin búsqueda), el resto en tarjetas, con buscador y 10 por página.
    """

    publicaciones = Publicacion.objects.filter(
        estado="publicado"
    ).select_related("autor").order_by("-fecha_publicacion")

    q = request.GET.get("q", "").strip()
    if q:
        publicaciones = publicaciones.filter(Q(titulo__icontains=q) | Q(contenido__icontains=q))

    pagina = Paginator(publicaciones, 10).get_page(request.GET.get("page"))

    elementos = list(pagina)
    for p in elementos:
        p.minutos_lectura = _minutos_lectura(p.contenido)

    destacada = None
    if pagina.number == 1 and not q and elementos:
        destacada, elementos = elementos[0], elementos[1:]

    return render(request, "publicaciones/lista.html", {
        "pagina": pagina,
        "destacada": destacada,
        "resto": elementos,
        "q": q,
    })


def detalle_publicacion(request, publicacion_id):

    publicacion = get_object_or_404(
        Publicacion,
        id=publicacion_id,
        estado="publicado"
    )

    publicacion.minutos_lectura = _minutos_lectura(publicacion.contenido)

    otras = Publicacion.objects.filter(
        estado="publicado"
    ).exclude(pk=publicacion.pk).order_by("-fecha_publicacion")[:3]

    return render(request, "publicaciones/detalle.html", {
        "publicacion": publicacion,
        "otras": otras,
    })


# ---------- Panel de gestión (Personal de Bienestar / Administrador) ----------
# CRUD como Class-Based Views, igual que ProgramaFormacion/Jornada/Ficha en usuarios.

class PublicacionListView(PersonalBienestarRequeridoMixin, ListView):
    model = Publicacion
    template_name = "publicaciones/panel_lista.html"
    context_object_name = "publicaciones"
    queryset = Publicacion.objects.select_related("autor")
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
    publicaciones = Publicacion.objects.select_related("autor").order_by("-fecha_creacion")

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
