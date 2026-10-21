from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from bienestar.forms import ConfiguracionBienestarForm, MiembroBienestarForm
from bienestar.models import ConfiguracionBienestar, ConstanciaHoras, MiembroBienestar
from bienestar.services.constancia import SinHorasError, emitir_constancia, generar_pdf_constancia
from bienestar.services.historial import historial_de, resumen_historial
from bienestar.services.progreso import calcular_progreso
from core.services.exportar import exportar_excel, exportar_word, exportar_pdf, responder_export
from usuarios.decorators import administrador_requerido, personal_bienestar_requerido


def nosotros(request):

    miembros = MiembroBienestar.objects.filter(
        estado="activo"
    ).order_by("nombre")

    return render(request, "bienestar/nosotros.html", {
        "miembros": miembros,
    })


# ---------- Panel de gestión (Personal de Bienestar / Administrador) ----------

@personal_bienestar_requerido
def panel_nosotros(request):

    miembros = MiembroBienestar.objects.order_by("nombre")

    return render(request, "bienestar/panel_lista.html", {
        "miembros": miembros,
    })


@personal_bienestar_requerido
def crear_miembro(request):

    form = MiembroBienestarForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Miembro de Bienestar creado correctamente.")
        return redirect("bienestar:panel_nosotros")

    return render(request, "bienestar/form.html", {
        "form": form,
        "titulo_pagina": "Agregar miembro de Bienestar",
    })


@personal_bienestar_requerido
def editar_miembro(request, miembro_id):

    miembro = get_object_or_404(MiembroBienestar, id=miembro_id)
    form = MiembroBienestarForm(request.POST or None, request.FILES or None, instance=miembro)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Miembro de Bienestar actualizado correctamente.")
        return redirect("bienestar:panel_nosotros")

    return render(request, "bienestar/form.html", {
        "form": form,
        "titulo_pagina": "Editar miembro de Bienestar",
    })


@personal_bienestar_requerido
def eliminar_miembro(request, miembro_id):

    miembro = get_object_or_404(MiembroBienestar, id=miembro_id)

    if request.method == "POST":
        miembro.delete()
        messages.success(request, "Miembro de Bienestar eliminado.")
        return redirect("bienestar:panel_nosotros")

    return render(request, "bienestar/confirmar_eliminar.html", {
        "miembro": miembro,
    })


@personal_bienestar_requerido
def exportar_miembros(request):
    miembros = MiembroBienestar.objects.order_by("nombre")

    encabezados = ["Nombre", "Cargo", "Correo para asesorías", "Estado"]
    filas = [
        [m.nombre, m.cargo, m.correo_asesorias, m.estado]
        for m in miembros
    ]

    formato = request.GET.get("formato")
    if formato == "excel":
        return exportar_excel("equipo_bienestar", "Equipo de Bienestar", encabezados, filas)
    if formato == "word":
        return exportar_word("equipo_bienestar", "Equipo de Bienestar", encabezados, filas)
    if formato == "pdf":
        return exportar_pdf("equipo_bienestar", "Equipo de Bienestar", encabezados, filas)

    messages.error(request, "Formato de exportación no válido.")
    return redirect("bienestar:panel_nosotros")


# ---------- Configuración (solo Administrador) ----------

@administrador_requerido
def configuracion(request):
    """
    Ajustes generales de Bienestar. Por ahora: la meta de horas que cada
    aprendiz debe completar (se muestra como barra de progreso en su panel).
    Solo el administrador puede cambiarla.
    """

    form = ConfiguracionBienestarForm(request.POST or None, instance=ConfiguracionBienestar.obtener())

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "La configuración se guardó correctamente.")
        return redirect("bienestar:configuracion")

    return render(request, "usuarios/panel_form.html", {
        "form": form,
        "titulo_pagina": "Configuración de Bienestar",
        "url_cancelar": "/usuarios/dashboard/",
    })


# ---------- Aprendiz: historial y constancia ----------

def _aprendiz_o_none(request):
    """El perfil de aprendiz de quien hace la petición (nunca de la URL)."""
    return getattr(request.user, "aprendiz", None)


@login_required(login_url="usuarios:login")
def mi_historial(request):
    """Historial completo de asistencia del aprendiz: todos sus eventos y sus horas."""

    aprendiz = _aprendiz_o_none(request)
    if aprendiz is None:
        return redirect("usuarios:dashboard")

    filas = historial_de(aprendiz)
    resumen = resumen_historial(filas)

    return render(request, "bienestar/mi_historial.html", {
        "filas": filas,
        "resumen": resumen,
        "progreso": calcular_progreso(resumen["horas"]),
    })


@login_required(login_url="usuarios:login")
def mi_historial_exportar(request):
    """El mismo historial en Excel / Word / PDF (con el membrete de Be Time)."""

    aprendiz = _aprendiz_o_none(request)
    if aprendiz is None:
        return redirect("usuarios:dashboard")

    q = request.GET.get("q", "").strip().lower()
    estado = request.GET.get("estado", "").strip()

    encabezados = ["Evento", "Lugar", "Fecha", "Estado", "Horas"]
    filas = []
    for f in historial_de(aprendiz):
        if estado and f.estado_codigo != estado:
            continue
        if q and q not in f"{f.evento} {f.lugar} {f.estado}".lower():
            continue
        filas.append([f.evento, f.lugar, f.fecha.strftime("%d/%m/%Y %I:%M %p"), f.estado, f.horas])

    return responder_export(
        request, "mi_historial_bienestar",
        "Mi historial de asistencia", encabezados, filas, "bienestar:mi_historial",
    )


@login_required(login_url="usuarios:login")
def descargar_constancia(request):
    """PDF de la constancia de horas del aprendiz, con código y QR de verificación."""

    aprendiz = _aprendiz_o_none(request)
    if aprendiz is None:
        return redirect("usuarios:dashboard")

    try:
        constancia = emitir_constancia(aprendiz)
    except SinHorasError as error:
        messages.warning(request, str(error))
        return redirect("usuarios:dashboard")

    url = request.build_absolute_uri(
        reverse("bienestar:verificar_constancia", args=[constancia.codigo])
    )
    pdf = generar_pdf_constancia(constancia, url)

    respuesta = HttpResponse(pdf, content_type="application/pdf")
    respuesta["Content-Disposition"] = f'attachment; filename="constancia_{constancia.codigo}.pdf"'
    return respuesta


def verificar_constancia(request, codigo):
    """
    Página PÚBLICA (sin sesión) para comprobar que una constancia es auténtica:
    quien recibe el PDF escanea el QR o escribe el código. Solo muestra lo
    necesario y con el documento parcialmente oculto.
    """
    constancia = ConstanciaHoras.objects.filter(codigo=codigo.strip().upper()).first()

    return render(request, "bienestar/verificar_constancia.html", {
        "constancia": constancia,
        "codigo": codigo,
    }, status=200 if constancia else 404)
