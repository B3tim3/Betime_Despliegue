"""
Pantallas de inicio (dashboard) de cada rol: aprendiz, Personal de Bienestar y Administrador.
"""

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from bienestar.services.progreso import calcular_progreso, horas_de
from eventos.models import Evento, Inscripcion
from eventos.services.estados import sincronizar_estados
from publicaciones.models import Publicacion
from usuarios.models import Aprendiz


@login_required(login_url="usuarios:login")
def dashboard_redirect(request):

    usuario = request.user

    if hasattr(usuario, "administrador"):
        return redirect("usuarios:dashboard_admin")

    if hasattr(usuario, "personal_bienestar"):
        return redirect("usuarios:dashboard_bienestar")

    if hasattr(usuario, "aprendiz"):
        return redirect("usuarios:dashboard_aprendiz")

    messages.warning(
        request,
        "Tu cuenta no tiene un perfil asignado todavía. Contacta al administrador."
    )
    logout(request)
    return redirect("usuarios:login")


@login_required(login_url="usuarios:login")
def dashboard_aprendiz(request):

    if not hasattr(request.user, "aprendiz"):
        return redirect("usuarios:dashboard")

    aprendiz = request.user.aprendiz

    # Solo cuentan las horas de eventos con asistencia marcada como "asistió"
    # (misma regla que el historial y la constancia en PDF).
    horas = horas_de(aprendiz).select_related(
        "asistencia__inscripcion__evento", "participacion__actividad"
    ).order_by("-fecha")

    total_horas = horas.aggregate(total=Sum("cantidad_horas"))["total"] or 0

    inscripciones = Inscripcion.objects.filter(
        aprendiz=aprendiz
    ).select_related("evento").order_by("-fecha_inscripcion")

    # Eventos abiertos a los que todavía no está inscrito (una inscripción
    # cancelada no cuenta: puede volver a inscribirse).
    proximos_eventos = Evento.objects.filter(
        estado="programado", fecha_inicio__gt=timezone.now()
    ).exclude(
        id__in=Inscripcion.objects.filter(aprendiz=aprendiz).exclude(
            estado="cancelada"
        ).values("evento_id")
    ).order_by("fecha_inicio")[:6]

    return render(request, "dashboard/aprendiz.html", {
        "proximos_eventos": proximos_eventos,
        "aprendiz": aprendiz,
        "horas": horas,
        "total_horas": total_horas,
        "progreso": calcular_progreso(total_horas),
        "inscripciones": inscripciones,
    })


def _resumen_del_panel():
    """Números y próximos eventos que se ven en el inicio de Bienestar y del administrador."""
    sincronizar_estados()
    vigentes = Evento.objects.filter(estado__in=["programado", "en_curso"])
    return {
        "total_aprendices_activos": Aprendiz.objects.filter(estado="activo").count(),
        "total_eventos_vigentes": vigentes.count(),
        "total_publicaciones": Publicacion.objects.filter(estado="publicado").count(),
        "eventos_vigentes": vigentes.annotate(
            total_inscritos=Count("inscripciones", filter=~Q(inscripciones__estado="cancelada"))
        ).order_by("fecha_inicio")[:5],
    }


@login_required(login_url="usuarios:login")
def dashboard_bienestar(request):

    if not hasattr(request.user, "personal_bienestar"):
        return redirect("usuarios:dashboard")

    return render(request, "dashboard/bienestar.html", {
        "personal_bienestar": request.user.personal_bienestar,
        **_resumen_del_panel(),
    })


@login_required(login_url="usuarios:login")
def dashboard_admin(request):

    if not hasattr(request.user, "administrador"):
        return redirect("usuarios:dashboard")

    return render(request, "dashboard/admin.html", {
        "administrador": request.user.administrador,
        **_resumen_del_panel(),
    })
