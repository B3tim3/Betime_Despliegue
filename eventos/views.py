from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from bienestar.services import registrar_asistencia_y_horas
from core.services.exportar import responder_export
from eventos.forms import EventoForm
from eventos.models import Evento, Inscripcion
from eventos.services import generar_imagen_qr
from usuarios.decorators import personal_bienestar_requerido
from usuarios.mixins import PersonalBienestarRequeridoMixin


def lista_eventos(request):

    eventos = Evento.objects.filter(
        fecha_inicio__gte=timezone.now()
    ).order_by("fecha_inicio")

    return render(request, "eventos/lista.html", {
        "eventos": eventos,
    })


def detalle_evento(request, evento_id):

    evento = get_object_or_404(Evento, id=evento_id)

    ya_inscrito = False
    if request.user.is_authenticated and hasattr(request.user, "aprendiz"):
        ya_inscrito = Inscripcion.objects.filter(
            evento=evento, aprendiz=request.user.aprendiz
        ).exclude(estado="cancelada").exists()

    return render(request, "eventos/detalle.html", {
        "evento": evento,
        "ya_inscrito": ya_inscrito,
    })


@login_required(login_url="usuarios:login")
def inscribirse_evento(request, evento_id):

    evento = get_object_or_404(Evento, id=evento_id)

    if not hasattr(request.user, "aprendiz"):
        messages.error(request, "Solo los aprendices pueden inscribirse a eventos.")
        return redirect("eventos:detalle", evento_id=evento.id)

    if evento.estado != "programado":
        messages.error(request, "Este evento ya no está abierto para inscripciones.")
        return redirect("eventos:detalle", evento_id=evento.id)

    if request.method == "POST":
        _, creada = Inscripcion.objects.get_or_create(
            evento=evento,
            aprendiz=request.user.aprendiz,
            defaults={"estado": "inscrito"},
        )

        if creada:
            messages.success(request, "Te inscribiste correctamente. ¡Nos vemos en el evento!")
        else:
            messages.info(request, "Ya estabas inscrito a este evento.")

    return redirect("eventos:detalle", evento_id=evento.id)


# ---------- Panel de gestión (Personal de Bienestar / Administrador) ----------
# CRUD como Class-Based Views, igual que ProgramaFormacion/Jornada/Ficha en usuarios.

class EventoListView(PersonalBienestarRequeridoMixin, ListView):
    model = Evento
    template_name = "eventos/panel_lista.html"
    context_object_name = "eventos"
    ordering = ["-fecha_inicio"]
    paginate_by = 15


class EventoCreateView(PersonalBienestarRequeridoMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/form.html"
    success_url = reverse_lazy("eventos:panel_lista")
    extra_context = {"titulo_pagina": "Crear evento"}

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, "Evento creado correctamente.")
        return super().form_valid(form)


class EventoUpdateView(PersonalBienestarRequeridoMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/form.html"
    success_url = reverse_lazy("eventos:panel_lista")
    extra_context = {"titulo_pagina": "Editar evento"}

    def form_valid(self, form):
        messages.success(self.request, "Evento actualizado correctamente.")
        return super().form_valid(form)


class EventoDeleteView(PersonalBienestarRequeridoMixin, DeleteView):
    model = Evento
    template_name = "eventos/confirmar_eliminar.html"
    context_object_name = "evento"
    success_url = reverse_lazy("eventos:panel_lista")

    def form_valid(self, form):
        messages.success(self.request, "Evento eliminado.")
        return super().form_valid(form)


@personal_bienestar_requerido
def exportar_eventos(request):
    eventos = Evento.objects.order_by("-fecha_inicio")

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


# ---------- Exportar los inscritos de un evento puntual ----------
# A diferencia de exportar_eventos (que exporta TODOS los eventos),
# esta exporta los inscritos de UN evento -- por eso el id del evento
# viaja como parámetro de la URL (?evento_id=), no en la ruta, así
# reutiliza el mismo componente de botones que ya usan las demás
# listas (ver export_extra_params en checklist_inscritos).

@personal_bienestar_requerido
def exportar_inscritos(request):
    evento_id = request.GET.get("evento_id")
    evento = get_object_or_404(Evento, id=evento_id)

    inscripciones = Inscripcion.objects.filter(
        evento=evento
    ).exclude(
        estado="cancelada"
    ).select_related(
        "aprendiz__usuario", "aprendiz__ficha", "asistencia"
    ).order_by("aprendiz__usuario__apellidos", "aprendiz__usuario__nombres")

    def horas_de(inscripcion):
        if not hasattr(inscripcion, "asistencia") or not inscripcion.asistencia.asistio:
            return ""
        registro = inscripcion.asistencia.horas_bienestar.first()
        return registro.cantidad_horas if registro else ""

    def asistio_texto(inscripcion):
        return "Sí" if hasattr(inscripcion, "asistencia") and inscripcion.asistencia.asistio else "No"

    encabezados = ["Aprendiz", "Tipo Documento", "Documento", "Ficha", "Asistió", "Horas"]
    filas = [
        [
            i.aprendiz.usuario.get_full_name(),
            i.aprendiz.usuario.tipo_documento,
            i.aprendiz.usuario.numero_documento,
            i.aprendiz.ficha.numero_ficha,
            asistio_texto(i),
            horas_de(i),
        ]
        for i in inscripciones
    ]

    return responder_export(
        request, "inscritos", f"Inscritos - {evento.titulo}", encabezados, filas, "eventos:panel_lista"
    )


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
        "aprendiz__usuario", "asistencia"
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

            registrar_asistencia_y_horas(
                inscripcion=inscripcion,
                asistio=asistio,
                cantidad_horas=cantidad_horas,
                motivo=f"Asistencia a: {evento.titulo}",
                asignado_por=request.user.personal_bienestar,
            )

        messages.success(request, "Asistencia y horas registradas correctamente.")
        return redirect("eventos:panel_inscritos", evento_id=evento.id)

    return render(request, "eventos/checklist_inscritos.html", {
        "evento": evento,
        "inscripciones": inscripciones,
        "export_extra_params": f"evento_id={evento.id}",
    })


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
    return render(request, "eventos/escanear_qr.html")


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
            "aprendiz__usuario", "aprendiz__ficha", "evento"
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

    if request.method == "POST" and hasattr(request.user, "personal_bienestar"):
        registrar_asistencia_y_horas(
            inscripcion=inscripcion,
            asistio=True,
            cantidad_horas=inscripcion.evento.horas_otorgadas,
            motivo=f"Asistencia a: {inscripcion.evento.titulo} (QR)",
            asignado_por=request.user.personal_bienestar,
        )
        messages.success(
            request,
            f"Asistencia confirmada para {inscripcion.aprendiz.usuario.get_full_name()}."
        )
        return redirect("eventos:confirmar_asistencia_qr", token=token)

    return render(request, "eventos/confirmar_asistencia_qr.html", {
        "inscripcion": inscripcion,
    })