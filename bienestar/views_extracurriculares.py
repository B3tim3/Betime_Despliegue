"""
Vistas de las horas de bienestar por mérito (fuera de eventos).

Aprendiz:  "Recibir horas de bienestar por mérito" -> ingresa un código o muestra su QR.
Bienestar: crea la actividad, comparte el código, asigna horas con checklist
           o escaneando el QR personal de cada aprendiz.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from bienestar.forms.extracurricular import ActividadExtracurricularForm
from bienestar.models import ActividadExtracurricular, ParticipacionExtracurricular
from bienestar.services import extracurriculares as svc
from core.services import periodos
from core.services.auditoria import registrar as auditar
from eventos.services.qr import generar_imagen_qr
from usuarios.decorators import personal_bienestar_requerido
from usuarios.models import Aprendiz


def _aprendiz(request):
    return getattr(request.user, "aprendiz", None) if request.user.is_authenticated else None


# ====================== APRENDIZ ======================

@login_required(login_url="usuarios:login")
def recibir_extracurriculares(request):
    aprendiz = _aprendiz(request)
    if aprendiz is None:
        return redirect("usuarios:dashboard")

    if request.method == "POST":
        try:
            participacion, creada = svc.unirse_con_codigo(aprendiz, request.POST.get("codigo", ""))
        except svc.ExtracurricularError as error:
            messages.error(request, str(error))
        else:
            titulo = participacion.actividad.titulo
            if participacion.estado == "otorgada":
                messages.info(request, f"Ya tienes tus horas de «{titulo}».")
            elif creada:
                messages.success(
                    request,
                    f"Quedaste en la lista de «{titulo}». Bienestar te asignará las horas y te avisará.")
            else:
                messages.info(request, f"Ya estabas en la lista de «{titulo}». Bienestar te asignará las horas.")
        return redirect("bienestar:recibir_extracurriculares")

    participaciones = (
        aprendiz.participaciones_extracurriculares
        .select_related("actividad", "horas").order_by("-actividad__fecha", "-id")[:10]
    )
    return render(request, "bienestar/extracurriculares/recibir.html", {
        "participaciones": participaciones,
    })


@login_required(login_url="usuarios:login")
def qr_extracurricular_imagen(request):
    """Imagen del QR personal. Solo la ve su dueño."""
    aprendiz = _aprendiz(request)
    if aprendiz is None:
        return HttpResponse(status=403)
    url = request.build_absolute_uri(
        reverse("bienestar:extracurricular_qr", args=[svc.token_qr_de(aprendiz)]))
    return HttpResponse(generar_imagen_qr(url).read(), content_type="image/png")


# ====================== BIENESTAR ======================

@personal_bienestar_requerido
def actividades_lista(request):
    periodo = periodos.resolver(request.GET.get("periodo"))
    actividades = periodos.filtrar(
        ActividadExtracurricular.objects.select_related("creado_por__usuario"),
        "fecha", periodo, como_fecha=True,
    ).annotate(
        total=Count("participaciones"),
        con_horas=Count("participaciones", filter=Q(participaciones__estado="otorgada")),
    )
    return render(request, "bienestar/extracurriculares/lista.html", {
        "actividades": actividades,
        "periodo": periodo,
        "opciones_periodo": periodos.opciones(ActividadExtracurricular.objects.all(), "fecha"),
    })


def _solo_personal(request, destino):
    """Administrador puede MIRAR, pero las horas las asigna Personal de Bienestar."""
    if hasattr(request.user, "personal_bienestar"):
        return None
    messages.error(request, "Solo Personal de Bienestar puede crear actividades y asignar horas.")
    return redirect(destino)


@personal_bienestar_requerido
def actividad_crear(request):
    denegado = _solo_personal(request, "bienestar:actividades_lista")
    if denegado:
        return denegado
    form = ActividadExtracurricularForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        actividad = form.save(commit=False)
        actividad.creado_por = request.user.personal_bienestar
        actividad.save()
        messages.success(request, f"Actividad creada. El código para los aprendices es {actividad.codigo}.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    return render(request, "bienestar/extracurriculares/form.html", {
        "form": form, "titulo_pagina": "Crear actividad por mérito"})


@personal_bienestar_requerido
def actividad_editar(request, actividad_id):
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)
    if not hasattr(request.user, "personal_bienestar"):
        messages.error(request, "Solo Personal de Bienestar puede editar actividades.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    form = ActividadExtracurricularForm(request.POST or None, instance=actividad)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Actividad actualizada. Las horas ya otorgadas no cambian.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    return render(request, "bienestar/extracurriculares/form.html", {
        "form": form, "titulo_pagina": "Editar actividad por mérito", "actividad": actividad})


@personal_bienestar_requerido
@require_POST
def actividad_estado(request, actividad_id):
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)
    if not hasattr(request.user, "personal_bienestar"):
        messages.error(request, "Solo Personal de Bienestar puede abrir o cerrar actividades.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    actividad.estado = "cerrada" if actividad.abierta else "abierta"
    actividad.save(update_fields=["estado"])
    messages.success(request, "Actividad cerrada: ya no recibe participantes." if not actividad.abierta
                     else "Actividad reabierta.")
    return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)


@personal_bienestar_requerido
@require_POST
def actividad_eliminar(request, actividad_id):
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)
    if not hasattr(request.user, "personal_bienestar"):
        messages.error(request, "Solo Personal de Bienestar puede eliminar actividades.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    if actividad.participaciones.filter(horas__isnull=False).exists():
        messages.error(
            request,
            "Esta actividad ya dio horas y es parte del historial de los aprendices, no se puede "
            "eliminar. Ciérrala para que no reciba más participantes.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    try:
        titulo = actividad.titulo
        actividad.delete()
    except ProtectedError:
        messages.error(request, "No se pudo eliminar: tiene horas registradas.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    messages.success(request, f"Actividad «{titulo}» eliminada.")
    return redirect("bienestar:actividades_lista")


def _filas(actividad):
    participaciones = list(
        actividad.participaciones
        .select_related("aprendiz__usuario", "aprendiz__grupo", "horas")
        .order_by("aprendiz__usuario__apellidos", "aprendiz__usuario__nombres")
    )
    for p in participaciones:
        registro = getattr(p, "horas", None)
        p.horas_guardadas = registro.cantidad_horas if (p.estado == "otorgada" and registro) else None
    return participaciones


@personal_bienestar_requerido
def actividad_detalle(request, actividad_id):
    """Checklist de la actividad: quién está en la lista y cuántas horas se le dan."""
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)

    if request.method == "POST":
        if not hasattr(request.user, "personal_bienestar"):
            messages.error(request, "Solo Personal de Bienestar puede asignar horas "
                                    "(un Administrador puede ver esta lista, pero no enviarla).")
            return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)

        personal = request.user.personal_bienestar
        cambios = 0
        for p in _filas(actividad):
            marcado = request.POST.get(f"dar_{p.id}") == "on"
            texto = request.POST.get(f"horas_{p.id}", "").strip()
            horas = int(texto) if texto.isdigit() else actividad.horas
            horas = max(1, min(horas, 40))

            # Misma idea que el checklist de eventos: la fila trae cómo estaba al
            # abrir la página; si no se tocó se salta, para no pisar lo que otra
            # persona hizo con el QR mientras tanto.
            inicial = request.POST.get(f"inicial_{p.id}")
            ahora = f"1|{horas}" if marcado else "0"
            if inicial is not None and inicial == ahora:
                continue

            if marcado:
                _, cambio = svc.otorgar_horas(
                    actividad=actividad, aprendiz=p.aprendiz, horas=horas,
                    asignado_por=personal, metodo="manual" if p.estado == "otorgada" else p.metodo,
                    request=request)
                cambios += cambio != "igual"
            else:
                _, quitada = svc.quitar_horas(participacion=p, asignado_por=personal, request=request)
                cambios += quitada
        messages.success(request, "Horas guardadas." if cambios else "No había cambios que guardar.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)

    filas = _filas(actividad)
    con_horas = sum(1 for p in filas if p.estado == "otorgada")
    return render(request, "bienestar/extracurriculares/detalle.html", {
        "actividad": actividad,
        "filas": filas,
        "total_con_horas": con_horas,
        "total_pendientes": len(filas) - con_horas,
    })


@personal_bienestar_requerido
@require_POST
def actividad_agregar(request, actividad_id):
    """Agrega a un aprendiz por documento (por si no tiene celular a la mano)."""
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)
    if not hasattr(request.user, "personal_bienestar"):
        messages.error(request, "Solo Personal de Bienestar puede agregar participantes.")
        return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)
    documento = "".join(request.POST.get("documento", "").split())
    aprendiz = Aprendiz.objects.select_related("usuario").filter(usuario__numero_documento=documento).first()
    if aprendiz is None:
        messages.error(request, "No hay ningún aprendiz con ese número de documento.")
    elif not actividad.abierta:
        messages.error(request, "La actividad está cerrada. Reábrela para agregar participantes.")
    else:
        _, creada = ParticipacionExtracurricular.objects.get_or_create(
            actividad=actividad, aprendiz=aprendiz, defaults={"metodo": "manual"})
        messages.success(request, f"{aprendiz.usuario.get_full_name()} agregado a la lista." if creada
                         else f"{aprendiz.usuario.get_full_name()} ya estaba en la lista.")
    return redirect("bienestar:actividad_detalle", actividad_id=actividad.id)


# ---------- Escáner de QR ----------

@personal_bienestar_requerido
def actividad_escanear(request, actividad_id):
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)
    return render(request, "bienestar/extracurriculares/escanear.html", {"actividad": actividad})


def _datos_aprendiz(aprendiz):
    return {"nombre": aprendiz.usuario.get_full_name(), "grupo": aprendiz.grupo.numero_grupo}


@personal_bienestar_requerido
@require_POST
def actividad_qr_rapido(request, actividad_id):
    """Modo continuo: recibe el token del QR personal y da las horas al instante (JSON)."""
    actividad = get_object_or_404(ActividadExtracurricular, id=actividad_id)
    if not hasattr(request.user, "personal_bienestar"):
        return JsonResponse({"ok": False, "mensaje": "Solo Personal de Bienestar puede asignar horas."}, status=403)
    personal = request.user.personal_bienestar

    aprendiz = svc.aprendiz_de_token(request.POST.get("token", ""))
    if aprendiz is None:
        return JsonResponse({"ok": False, "mensaje": "Ese QR no es un QR de horas por mérito de Be Time."}, status=404)
    datos = _datos_aprendiz(aprendiz)

    if request.POST.get("accion") == "deshacer":
        participacion = ParticipacionExtracurricular.objects.filter(actividad=actividad, aprendiz=aprendiz).first()
        if participacion is not None:
            svc.quitar_horas(participacion=participacion, asignado_por=personal, request=request)
        return JsonResponse({"ok": True, "estado": "deshecho", **datos, "mensaje": "Horas retiradas."})

    if not actividad.abierta:
        return JsonResponse({"ok": False, "estado": "rechazado", **datos,
                             "mensaje": "La actividad está cerrada."}, status=409)

    _, cambio = svc.otorgar_horas(
        actividad=actividad, aprendiz=aprendiz, horas=actividad.horas,
        asignado_por=personal, metodo="qr", request=request)
    if cambio == "igual":
        return JsonResponse({"ok": True, "estado": "ya_estaba", **datos, "mensaje": "Ya tenía sus horas."})
    return JsonResponse({"ok": True, "estado": "confirmado", **datos,
                         "mensaje": f"{actividad.horas} hora{'s' if actividad.horas != 1 else ''} asignada{'s' if actividad.horas != 1 else ''}."})


@login_required(login_url="usuarios:login")
def extracurricular_qr(request, token):
    """
    A esta URL lleva el QR personal si se escanea con la cámara normal del celular:
    Bienestar elige a qué actividad abierta darle las horas.
    """
    aprendiz = svc.aprendiz_de_token(token)
    if aprendiz is None:
        messages.error(request, "Ese código QR no es válido.")
        return redirect("usuarios:dashboard")
    if not (hasattr(request.user, "personal_bienestar") or hasattr(request.user, "administrador")):
        messages.error(request, "Solo Personal de Bienestar puede usar este código.")
        return redirect("usuarios:dashboard")

    abiertas = ActividadExtracurricular.objects.filter(estado="abierta")

    if request.method == "POST":
        if not hasattr(request.user, "personal_bienestar"):
            messages.error(request, "Solo Personal de Bienestar puede asignar horas.")
            return redirect("bienestar:extracurricular_qr", token=token)
        actividad = abiertas.filter(pk=request.POST.get("actividad") or 0).first()
        if actividad is None:
            messages.error(request, "Elige una actividad abierta.")
            return redirect("bienestar:extracurricular_qr", token=token)
        _, cambio = svc.otorgar_horas(
            actividad=actividad, aprendiz=aprendiz, horas=actividad.horas,
            asignado_por=request.user.personal_bienestar, metodo="qr", request=request)
        nombre = aprendiz.usuario.get_full_name()
        if cambio == "igual":
            messages.info(request, f"{nombre} ya tenía las horas de «{actividad.titulo}».")
        else:
            messages.success(request, f"Horas asignadas a {nombre} en «{actividad.titulo}».")
        return redirect("bienestar:extracurricular_qr", token=token)

    return render(request, "bienestar/extracurriculares/confirmar_qr.html", {
        "aprendiz": aprendiz, "abiertas": abiertas,
    })
