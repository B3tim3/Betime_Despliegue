import hmac
import os

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from notificaciones.models import Notificacion
from notificaciones.services.recordatorios import HORAS_POR_DEFECTO, enviar_recordatorios


@login_required(login_url="usuarios:login")
def lista_notificaciones(request):
    """Todas las notificaciones del usuario, las más nuevas primero."""

    solo_no_leidas = request.GET.get("solo") == "no_leidas"

    notificaciones = Notificacion.objects.filter(usuario=request.user)
    if solo_no_leidas:
        notificaciones = notificaciones.filter(leida=False)

    pagina = Paginator(notificaciones, 20).get_page(request.GET.get("page"))

    return render(request, "notificaciones/lista.html", {
        "pagina": pagina,
        "solo_no_leidas": solo_no_leidas,
        "total_no_leidas": Notificacion.objects.filter(usuario=request.user, leida=False).count(),
    })


@login_required(login_url="usuarios:login")
def abrir_notificacion(request, notificacion_id):
    """
    La marca como leída y lleva al usuario a lo que la notificación
    señala. Solo redirige a rutas internas (que empiezan con "/") para
    que nadie pueda usar una notificación como puerta a otro sitio.
    """
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)

    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=["leida"])

    destino = notificacion.url
    if destino.startswith("/") and not destino.startswith("//"):
        return redirect(destino)
    return redirect("notificaciones:lista")


@login_required(login_url="usuarios:login")
@require_POST
def marcar_leida(request, notificacion_id):
    Notificacion.objects.filter(id=notificacion_id, usuario=request.user).update(leida=True)
    return redirect(request.POST.get("next") if request.POST.get("next", "").startswith("/") else "notificaciones:lista")


@login_required(login_url="usuarios:login")
@require_POST
def marcar_todas_leidas(request):
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return redirect("notificaciones:lista")


@csrf_exempt
def ejecutar_recordatorios(request):
    """
    Puerta para un "cron externo" (por ejemplo cron-job.org) cuando el
    hosting no permite tareas programadas. Está apagada a menos que
    exista la variable de entorno RECORDATORIOS_TOKEN; con ella, hay que
    mandar el mismo valor en el encabezado  Authorization: Bearer <token>
    o en ?token=<token>.
    """
    esperado = os.environ.get("RECORDATORIOS_TOKEN", "")
    if not esperado:
        raise Http404()

    recibido = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    recibido = recibido or request.GET.get("token", "")

    if not hmac.compare_digest(recibido.encode(), esperado.encode()):
        return HttpResponseForbidden("Token inválido.")

    try:
        horas = int(request.GET.get("horas", HORAS_POR_DEFECTO))
    except ValueError:
        horas = HORAS_POR_DEFECTO
    horas = max(1, min(horas, 24 * 7))

    return JsonResponse(enviar_recordatorios(horas=horas))
