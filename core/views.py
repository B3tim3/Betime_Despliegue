from django.shortcuts import render
from django.utils import timezone

from eventos.models import Evento
from publicaciones.models import Publicacion


def index(request):

    publicaciones = Publicacion.objects.filter(
        estado="publicado"
    ).order_by("-fecha_publicacion")[:3]

    eventos = Evento.objects.filter(
        fecha_inicio__gte=timezone.now()
    ).order_by("fecha_inicio")[:3]

    return render(request, "pages/index.html", {
        "publicaciones": publicaciones,
        "eventos": eventos,
    })
