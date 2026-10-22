from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from core.models import RegistroAuditoria
from eventos.models import Evento
from publicaciones.models import Publicacion
from usuarios.decorators import administrador_requerido


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


@administrador_requerido
def auditoria(request):
    """Bitácora de acciones sensibles (solo lectura, solo Administrador)."""

    registros = RegistroAuditoria.objects.all()

    accion = request.GET.get("accion", "").strip()
    if accion in dict(RegistroAuditoria.ACCIONES):
        registros = registros.filter(accion=accion)
    else:
        accion = ""

    q = request.GET.get("q", "").strip()
    if q:
        registros = registros.filter(Q(usuario_texto__icontains=q) | Q(descripcion__icontains=q))

    pagina = Paginator(registros, 30).get_page(request.GET.get("page"))

    return render(request, "auditoria/lista.html", {
        "pagina": pagina,
        "acciones": RegistroAuditoria.ACCIONES,
        "accion": accion,
        "q": q,
    })
