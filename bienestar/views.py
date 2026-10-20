from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from bienestar.forms import MiembroBienestarForm
from bienestar.models import MiembroBienestar
from core.services.exportar import exportar_excel, exportar_word, exportar_pdf
from usuarios.decorators import personal_bienestar_requerido


def nosotros(request):

    categoria_seleccionada = request.GET.get("categoria", "")

    miembros = MiembroBienestar.objects.filter(
        estado="activo"
    ).order_by("nombre")

    if categoria_seleccionada:
        miembros = miembros.filter(categoria=categoria_seleccionada)

    return render(request, "bienestar/nosotros.html", {
        "miembros": miembros,
        "categorias": MiembroBienestar.CATEGORIA_CHOICES,
        "categoria_seleccionada": categoria_seleccionada,
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
