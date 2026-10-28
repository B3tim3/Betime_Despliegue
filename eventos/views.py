from django.contrib import messages
import re

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from bienestar.services import registrar_asistencia_y_horas
from core.services.auditoria import registrar as auditar
from core.services.exportar import responder_export
from eventos.forms import EventoForm
from eventos.models import Evento, Inscripcion
from eventos.services import generar_imagen_qr
from eventos.services.avisos import (
    avisar_cambios_evento, avisar_evento_eliminado, avisar_evento_nuevo,
)
from eventos.services.estados import sincronizar_estados
from eventos.services.inscripciones import InscripcionError, cancelar, inscribir, motivo_no_confirmable
from usuarios.services.datos_aprendiz import DatosAprendiz, SELECT_RELATED_APRENDIZ
from usuarios.decorators import personal_bienestar_requerido
from usuarios.mixins import PersonalBienestarRequeridoMixin


def lista_eventos(request):

    sincronizar_estados()

    # Incluye los que están en curso (ya empezaron pero no terminan): por eso se
    # filtra por fecha_fin y no por fecha_inicio.
    eventos = Evento.objects.exclude(estado="cancelado").filter(
        fecha_fin__gte=timezone.now()
    ).order_by("fecha_inicio")

    return render(request, "eventos/lista.html", {
        "eventos": eventos,
    })


def detalle_evento(request, evento_id):

    sincronizar_estados()
    evento = get_object_or_404(Evento, id=evento_id)

    inscripcion = None
    if request.user.is_authenticated and hasattr(request.user, "aprendiz"):
        inscripcion = Inscripcion.objects.filter(
            evento=evento, aprendiz=request.user.aprendiz
        ).exclude(estado="cancelada").select_related("evento").first()

    return render(request, "eventos/detalle.html", {
        "evento": evento,
        "ya_inscrito": inscripcion is not None,
        "inscripcion": inscripcion,
    })


def _volver(request, por_defecto, **kwargs):
    """
    Adónde regresar tras inscribirse/cancelar: la pantalla desde donde
    se hizo el clic (campo oculto "next"), solo si es una ruta de este
    mismo sitio; si no, la pantalla por defecto.
    """
    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return redirect(destino)
    return redirect(por_defecto, **kwargs)


@login_required(login_url="usuarios:login")
def inscribirse_evento(request, evento_id):

    sincronizar_estados()
    evento = get_object_or_404(Evento, id=evento_id)

    if not hasattr(request.user, "aprendiz"):
        messages.error(request, "Solo los aprendices pueden inscribirse a eventos.")
        return redirect("eventos:detalle", evento_id=evento.id)

    if request.method == "POST":
        try:
            _, accion = inscribir(request.user.aprendiz, evento)
        except InscripcionError as error:
            messages.error(request, str(error))
        else:
            if accion == "existente":
                messages.info(request, "Ya estabas inscrito a este evento.")
            else:
                messages.success(request, "Te inscribiste correctamente. ¡Nos vemos en el evento!")
    elif evento.estado_actual != "programado":
        messages.error(request, "Este evento ya no está abierto para inscripciones.")

    return _volver(request, "eventos:detalle", evento_id=evento.id)


@login_required(login_url="usuarios:login")
@require_POST
def cancelar_inscripcion(request, inscripcion_id):
    """El aprendiz cancela SU inscripción (nunca la de otra persona)."""

    if not hasattr(request.user, "aprendiz"):
        messages.error(request, "Solo los aprendices tienen inscripciones.")
        return redirect("usuarios:dashboard")

    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related("evento", "aprendiz__usuario"),
        id=inscripcion_id, aprendiz=request.user.aprendiz,
    )

    try:
        cancelar(inscripcion)
    except InscripcionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Cancelaste tu inscripción a «{inscripcion.evento.titulo}».")

    return _volver(request, "usuarios:dashboard_aprendiz")


# ---------- Panel de gestión (Personal de Bienestar / Administrador) ----------
# CRUD como Class-Based Views, igual que ProgramaFormacion/Jornada/Grupo en usuarios.

class EventoListView(PersonalBienestarRequeridoMixin, ListView):
    model = Evento
    template_name = "eventos/panel_lista.html"
    context_object_name = "eventos"
    queryset = Evento.objects.select_related("creado_por")
    ordering = ["-fecha_inicio"]
    paginate_by = 15

    def get_queryset(self):
        sincronizar_estados()   # el panel siempre muestra el estado de ahora
        return super().get_queryset()


class EventoCreateView(PersonalBienestarRequeridoMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/form.html"
    success_url = reverse_lazy("eventos:panel_lista")
    extra_context = {"titulo_pagina": "Crear evento"}

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Evento creado correctamente.")
        respuesta = super().form_valid(form)
        avisar_evento_nuevo(self.object)
        return respuesta


class EventoUpdateView(PersonalBienestarRequeridoMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/form.html"
    success_url = reverse_lazy("eventos:panel_lista")
    extra_context = {"titulo_pagina": "Editar evento"}

    def form_valid(self, form):
        # form.instance ya trae los valores nuevos; el estado "de antes" hay
        # que leerlo de la base de datos, que todavía no se ha guardado.
        anterior = Evento.objects.get(pk=self.object.pk)
        messages.success(self.request, "Evento actualizado correctamente.")
        respuesta = super().form_valid(form)
        avisar_cambios_evento(anterior, self.object)
        if anterior.estado != "cancelado" and self.object.estado == "cancelado":
            auditar(
                "evento_cancelado", f"Se canceló el evento «{self.object.titulo}».",
                request=self.request, detalles={"evento_id": self.object.pk},
            )
        return respuesta


class EventoDeleteView(PersonalBienestarRequeridoMixin, DeleteView):
    model = Evento
    template_name = "eventos/confirmar_eliminar.html"
    context_object_name = "evento"
    success_url = reverse_lazy("eventos:panel_lista")

    def form_valid(self, form):
        avisar_evento_eliminado(self.object)
        auditar(
            "evento_eliminado",
            f"Se eliminó el evento «{self.object.titulo}» ({self.object.inscripciones.count()} inscripciones).",
            request=self.request, detalles={"evento_id": self.object.pk},
        )
        messages.success(self.request, "Evento eliminado.")
        return super().form_valid(form)


@personal_bienestar_requerido
def exportar_eventos(request):
    sincronizar_estados()
    eventos = Evento.objects.select_related("creado_por").order_by("-fecha_inicio")

    q = request.GET.get("q", "").strip()
    if q:
        eventos = eventos.filter(Q(titulo__icontains=q) | Q(lugar__icontains=q))

    estado = request.GET.get("estado", "").strip()
    if estado:
        eventos = eventos.filter(estado=estado)

    encabezados = ["Título", "Lugar", "Fecha inicio", "Fecha fin", "Horas", "Estado", "Creado por"]
    filas = [
        [
            e.titulo, e.lugar, e.fecha_inicio, e.fecha_fin,
            e.horas_otorgadas, e.estado, e.creado_por.get_full_name(),
        ]
        for e in eventos
    ]

    return responder_export(request, "eventos", "Eventos", encabezados, filas, "eventos:panel_lista")


# ---------- Checklist de asistencia y horas de bienestar ----------
# El "checklist manual" del que habla el roadmap: Bienestar entra a un
# evento, ve a todos los inscritos, marca quién asistió y con cuántas
# horas -- todo en una sola pantalla. Solo Personal de Bienestar puede
# ENVIAR el checklist (asignar horas), aunque Administrador también
# puede entrar a mirarlo, porque HorasBienestar.asignado_por solo
# acepta un PersonalBienestar, no un Administrador (así quedó
# diseñado el modelo desde el principio).

@personal_bienestar_requerido
def checklist_inscritos(request, evento_id):

    evento = get_object_or_404(Evento, id=evento_id)

    inscripciones = Inscripcion.objects.filter(
        evento=evento
    ).exclude(
        estado="cancelada"
    ).select_related(
        *[f"aprendiz__{relacion}" for relacion in SELECT_RELATED_APRENDIZ], "asistencia"
    ).prefetch_related(
        "asistencia__horas_bienestar"
    ).order_by("aprendiz__usuario__apellidos", "aprendiz__usuario__nombres")

    if request.method == "POST":

        if not hasattr(request.user, "personal_bienestar"):
            messages.error(
                request,
                "Solo Personal de Bienestar puede otorgar horas (un Administrador "
                "puede ver este checklist, pero no enviarlo)."
            )
            return redirect("eventos:panel_inscritos", evento_id=evento.id)

        for inscripcion in inscripciones:
            asistio = request.POST.get(f"asistio_{inscripcion.id}") == "on"
            horas_texto = request.POST.get(f"horas_{inscripcion.id}", "").strip()
            cantidad_horas = int(horas_texto) if horas_texto.isdigit() else 0

            # Cada fila trae escondido cómo estaba cuando se ABRIÓ la página
            # ("1|2" = asistió con 2 horas, "0" = pendiente). Si esa fila no
            # se tocó, se salta: así guardar el checklist no pisa lo que otra
            # persona de Bienestar confirmó con el QR mientras esta página
            # estaba abierta. Si el campo no viene (formulario viejo), se
            # comporta como antes y guarda todo.
            inicial = request.POST.get(f"inicial_{inscripcion.id}")
            if inicial is not None:
                ahora_texto = f"1|{cantidad_horas}" if asistio else "0"
                if inicial == ahora_texto:
                    continue

            registrar_asistencia_y_horas(
                inscripcion=inscripcion,
                asistio=asistio,
                cantidad_horas=cantidad_horas,
                motivo=f"Asistencia a: {evento.titulo}",
                asignado_por=request.user.personal_bienestar,
            )

        messages.success(request, "Asistencia y horas registradas correctamente.")
        return redirect("eventos:panel_inscritos", evento_id=evento.id)

    inscripciones = list(inscripciones)
    for inscripcion in inscripciones:
        # Todos los datos del aprendiz que pide Bienestar, ya listos
        # para mostrar (la misma fuente que usan las exportaciones).
        inscripcion.datos = DatosAprendiz.de(inscripcion.aprendiz)
        # Horas que ya se le otorgaron (si las hay), para no mostrar
        # siempre el valor por defecto del evento y evitar que al volver
        # a guardar el checklist se pisen horas ajustadas a mano.
        inscripcion.horas_guardadas = _horas_otorgadas(inscripcion)

    total_asistieron = sum(1 for i in inscripciones if getattr(getattr(i, "asistencia", None), "asistio", False))

    return render(request, "eventos/checklist_inscritos.html", {
        "evento": evento,
        "inscripciones": inscripciones,
        "total_asistieron": total_asistieron,
        "total_pendientes": len(inscripciones) - total_asistieron,
        # El botón "Exportar" lo anexa a la URL: así el archivo es de ESTE evento.
        "export_extra_params": f"evento_id={evento.id}",
    })


def _horas_otorgadas(inscripcion):
    """Suma de horas ya registradas para esta inscripción (None si no hay)."""
    asistencia = getattr(inscripcion, "asistencia", None)
    if asistencia is None:
        return None
    horas = [h.cantidad_horas for h in asistencia.horas_bienestar.all()]
    return sum(horas) if horas else None


def _texto_seguro(texto):
    """Quita los caracteres que Excel no admite en el nombre de una hoja ([ ] : * ? / \\)."""
    return re.sub(r"[\[\]:*?/\\]", " ", texto).strip()


@personal_bienestar_requerido
def exportar_inscritos(request):
    """
    Lista de asistencia de un evento en Excel / Word / PDF, con los datos
    del aprendiz que pide Bienestar. Replica el listado que antes se
    llenaba a mano (sin horas ni firma: la firma física no se necesita en el sistema).

    Parámetros: ?evento_id=<id>  (lo agrega el botón de la pantalla)
                ?q=<texto>       (lo agrega el buscador: se exporta solo lo filtrado)
    """
    evento_id = request.GET.get("evento_id", "")

    if not evento_id.isdigit():
        messages.error(request, "Falta indicar de qué evento es la lista.")
        return redirect("eventos:panel_lista")

    evento = get_object_or_404(Evento, id=evento_id)

    inscripciones = Inscripcion.objects.filter(
        evento=evento
    ).exclude(
        estado="cancelada"
    ).select_related(
        *[f"aprendiz__{relacion}" for relacion in SELECT_RELATED_APRENDIZ], "asistencia"
    ).prefetch_related(
        "asistencia__horas_bienestar"
    ).order_by("aprendiz__usuario__apellidos", "aprendiz__usuario__nombres")

    q = request.GET.get("q", "").strip().lower()

    encabezados = ["N°", *DatosAprendiz.ENCABEZADOS, "Asistió"]
    filas = []

    for inscripcion in inscripciones:
        datos = DatosAprendiz.de(inscripcion.aprendiz)
        asistio = bool(getattr(inscripcion, "asistencia", None) and inscripcion.asistencia.asistio)
        estado = "Sí" if asistio else "Pendiente"

        # Mismo criterio que el buscador de la pantalla: el texto escrito
        # puede estar en cualquier dato de la fila.
        if q and q not in f"{datos.texto_busqueda()} {estado.lower()}":
            continue

        filas.append([len(filas) + 1, *datos.como_fila(), estado])

    fecha = timezone.localtime(evento.fecha_inicio).strftime("%d/%m/%Y")
    titulo = _texto_seguro(f"Asistencia - {evento.titulo} - {fecha}")

    return responder_export(
        request, f"asistencia_evento_{evento.id}", titulo, encabezados, filas, "eventos:panel_lista"
    )


# ---------- QR: mecanismo alterno al checklist manual ----------
# El aprendiz ve su QR desde "Mi panel"; el funcionario lo escanea (con
# la cámara del celular o con el escáner de la app) y confirma la
# asistencia. Por debajo, llama exactamente al mismo servicio que usa
# el checklist manual -- si uno de los dos mecanismos falla, el otro
# sigue funcionando igual, porque no comparten ningún código frágil,
# solo el mismo servicio ya probado.

@login_required(login_url="usuarios:login")
def mi_qr_inscripcion(request, inscripcion_id):
    """
    Pantalla que ve el APRENDIZ con su propio código QR para un
    evento al que está inscrito.
    """

    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)

    if not hasattr(request.user, "aprendiz") or inscripcion.aprendiz != request.user.aprendiz:
        messages.error(request, "No tienes permiso para ver este código.")
        return redirect("usuarios:dashboard")

    if inscripcion.estado == "cancelada":
        messages.error(request, "Cancelaste esta inscripción, por eso ya no tiene código QR.")
        return redirect("usuarios:dashboard_aprendiz")

    return render(request, "eventos/mi_qr.html", {
        "inscripcion": inscripcion,
    })


@login_required(login_url="usuarios:login")
def qr_imagen_inscripcion(request, inscripcion_id):
    """
    Devuelve la IMAGEN del QR (el <img src="..."> de la plantilla
    anterior apunta aquí). Mismo control de permisos que la pantalla
    que lo muestra -- nadie puede pedir el QR de otra persona solo
    cambiando el número en la URL.
    """

    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)

    if not hasattr(request.user, "aprendiz") or inscripcion.aprendiz != request.user.aprendiz:
        return HttpResponse(status=403)

    url_confirmacion = request.build_absolute_uri(
        reverse_lazy("eventos:confirmar_asistencia_qr", args=[inscripcion.token])
    )

    buffer = generar_imagen_qr(url_confirmacion)
    return HttpResponse(buffer.read(), content_type="image/png")


@personal_bienestar_requerido
def escanear_qr(request):
    """
    Pantalla con la cámara para que Bienestar/Administrador escaneen
    el QR de un aprendiz sin salir de Be Time. También sirve escanear
    con la app de cámara normal del celular -- esta pantalla es solo
    una comodidad extra, no la única forma de hacerlo.
    """
    # Si se llegó desde el checklist de un evento, el botón "Escanear QR" manda
    # ?evento=<id>: así el enlace de arriba puede regresar justo a ese checklist
    # en vez de sacar a la persona del panel. Si el dato no sirve, se ignora.
    evento = None
    evento_id = request.GET.get("evento", "")
    if evento_id.isdigit():
        evento = Evento.objects.filter(pk=int(evento_id)).first()
    return render(request, "eventos/escanear_qr.html", {"evento": evento})


def confirmar_asistencia_qr(request, token):
    """
    A esta URL es a la que lleva el QR. Cualquiera puede ABRIRLA (por
    eso no tiene decorador de permisos arriba), pero solo alguien
    logueado como Personal de Bienestar puede de verdad CONFIRMAR --
    así, aunque el aprendiz mismo llegara a escanear su propio QR por
    curiosidad, no puede marcarse presente a sí mismo.
    """

    inscripcion = get_object_or_404(
        Inscripcion.objects.select_related(
            "aprendiz__usuario", "aprendiz__grupo", "evento"
        ),
        token=token,
    )

    if not request.user.is_authenticated:
        messages.info(request, "Inicia sesión como Personal de Bienestar para confirmar la asistencia.")
        return redirect("usuarios:login_personal")

    if not hasattr(request.user, "personal_bienestar"):
        messages.error(
            request,
            "Solo Personal de Bienestar puede confirmar asistencia por QR "
            "(un Administrador puede ver esta pantalla, pero no confirmarla)."
        )

    motivo = motivo_no_confirmable(inscripcion)

    if request.method == "POST" and hasattr(request.user, "personal_bienestar"):
        if motivo:
            messages.error(request, motivo)
            return redirect("eventos:confirmar_asistencia_qr", token=token)
        registrar_asistencia_y_horas(
            inscripcion=inscripcion,
            asistio=True,
            cantidad_horas=inscripcion.evento.horas_otorgadas,
            motivo=f"Asistencia a: {inscripcion.evento.titulo} (QR)",
            asignado_por=request.user.personal_bienestar,
            metodo="QR",
        )
        messages.success(
            request,
            f"Asistencia confirmada para {inscripcion.aprendiz.usuario.get_full_name()}."
        )
        return redirect("eventos:confirmar_asistencia_qr", token=token)

    return render(request, "eventos/confirmar_asistencia_qr.html", {
        "inscripcion": inscripcion,
        "motivo": motivo,
    })


@personal_bienestar_requerido
@require_POST
def confirmar_asistencia_qr_rapido(request, token):
    """
    Versión para el modo de escaneo continuo: recibe el token de un QR,
    confirma y responde JSON corto, sin cambiar de página. Así una sola
    persona puede escanear una fila de aprendices seguidos con un celular.

    Solo Personal de Bienestar (igual que la confirmación normal). Con
    accion=deshacer revierte una confirmación hecha por equivocación.
    Escanear dos veces el mismo QR no duplica nada: responde "ya estaba".
    """
    if not hasattr(request.user, "personal_bienestar"):
        return JsonResponse(
            {"ok": False, "mensaje": "Solo Personal de Bienestar puede confirmar asistencia."},
            status=403,
        )

    inscripcion = Inscripcion.objects.select_related(
        "aprendiz__usuario", "aprendiz__grupo", "evento", "asistencia"
    ).filter(token=token).first()
    if inscripcion is None:
        return JsonResponse({"ok": False, "mensaje": "Ese código QR no corresponde a ninguna inscripción."}, status=404)

    aprendiz = inscripcion.aprendiz.usuario
    datos = {"nombre": aprendiz.get_full_name(), "grupo": inscripcion.aprendiz.grupo.numero_grupo,
             "evento": inscripcion.evento.titulo}
    personal = request.user.personal_bienestar

    if request.POST.get("accion") == "deshacer":
        registrar_asistencia_y_horas(
            inscripcion=inscripcion, asistio=False, cantidad_horas=0,
            motivo=f"Asistencia a: {inscripcion.evento.titulo} (QR, deshecha)",
            asignado_por=personal, metodo="QR",
        )
        return JsonResponse({"ok": True, "estado": "deshecho", **datos, "mensaje": "Confirmación deshecha."})

    motivo = motivo_no_confirmable(inscripcion)
    if motivo:
        return JsonResponse({"ok": False, "estado": "rechazado", **datos, "mensaje": motivo}, status=409)

    asistencia = getattr(inscripcion, "asistencia", None)
    if asistencia is not None and asistencia.asistio:
        return JsonResponse({"ok": True, "estado": "ya_estaba", **datos, "mensaje": "Ya estaba confirmado."})

    registrar_asistencia_y_horas(
        inscripcion=inscripcion, asistio=True,
        cantidad_horas=inscripcion.evento.horas_otorgadas,
        motivo=f"Asistencia a: {inscripcion.evento.titulo} (QR)",
        asignado_por=personal, metodo="QR",
    )
    return JsonResponse({"ok": True, "estado": "confirmado", **datos, "mensaje": "Asistencia confirmada."})