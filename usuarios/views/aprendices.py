"""
Gestión de aprendices desde el panel (Personal de Bienestar y Administrador).
"""

from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DeleteView, UpdateView

from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from core.services.auditoria import registrar as auditar
from usuarios.filters import AprendizFilter
from usuarios.forms import AprendizEstadoForm
from usuarios.mixins import PersonalBienestarRequeridoMixin
from usuarios.models import Aprendiz, Grupo
from usuarios.tables import AprendizTable


# ---------- Aprendices (Personal de Bienestar o Administrador) ----------
# Se crean por auto-registro; aquí solo se consultan y se reasigna
# su grupo/estado (activo, retirado, egresado). No se crean ni se
# eliminan desde este panel.
#
# Igual que GrupoListView: la misma vista sirve para "todos los
# aprendices" (panel/aprendices/) y para "los aprendices de una
# grupo" (panel/grupos/<id>/aprendices/).

class AprendizListView(PersonalBienestarRequeridoMixin, SingleTableMixin, FilterView):
    """
    Piloto de django-tables2 + django-filter, en reemplazo del buscador
    y el orden-por-clic que antes hacíamos a mano en JS (tabla-filtro.js
    sigue existiendo y sigue activo en las otras 5 listas del panel,
    todavía no migradas).

    La ganancia real: ordenar y buscar ahora pasan por la base de
    datos, así que sí funcionan correctamente combinados con
    paginación (antes, buscar en la página 1 no encontraba algo que
    estuviera en la página 2).
    """

    model = Aprendiz
    table_class = AprendizTable
    filterset_class = AprendizFilter
    template_name = "usuarios/aprendices_list.html"
    table_pagination = {"per_page": 15}

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "usuario", "grupo", "grupo__programa_formacion"
        )

        grupo_id = self.kwargs.get("grupo_id")
        if grupo_id:
            queryset = queryset.filter(grupo_id=grupo_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        grupo_id = self.kwargs.get("grupo_id")
        if grupo_id:
            context["grupo"] = get_object_or_404(
                Grupo.objects.select_related("programa_formacion"), pk=grupo_id
            )

        # Para que "Exportar" traiga lo mismo que se ve filtrado en
        # pantalla: como la búsqueda ahora es un <form method="get">
        # de verdad, la URL actual ya tiene ?q=...&estado=... — solo
        # hay que copiarlo (menos "page") al link de exportar. Además
        # de eso, si venimos filtrados por grupo (que es parte de la
        # URL, no un ?parametro=), lo agregamos aparte.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)

        partes_extra = []
        if parametros:
            partes_extra.append(parametros.urlencode())
        if grupo_id:
            partes_extra.append(f"grupo_id={grupo_id}")

        if partes_extra:
            context["export_extra_params"] = "&".join(partes_extra)

        return context


class AprendizUpdateView(PersonalBienestarRequeridoMixin, UpdateView):
    model = Aprendiz
    form_class = AprendizEstadoForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:aprendices_lista")
    extra_context = {
        "titulo_pagina": "Editar aprendiz",
        "url_cancelar": reverse_lazy("usuarios:aprendices_lista"),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Que quede claro a QUIÉN se está editando (sobre todo al cambiar de grupo).
        context["titulo_pagina"] = f"Editar aprendiz: {self.object.usuario.get_full_name()}"
        return context

    def form_valid(self, form):
        # form.instance ya trae los valores nuevos; los de antes se leen de la base.
        anterior = Aprendiz.objects.select_related("grupo").get(pk=self.object.pk)
        cambios = {}
        for campo in form.changed_data:
            antes, despues = getattr(anterior, campo), form.cleaned_data[campo]
            cambios[campo] = {"antes": str(antes), "despues": str(despues)}

        messages.success(self.request, "Aprendiz actualizado correctamente.")
        respuesta = super().form_valid(form)

        if cambios:
            auditar(
                "aprendiz_editado",
                f"Se editó al aprendiz {self.object.usuario.get_full_name()} "
                f"({self.object.usuario.numero_documento}): {', '.join(cambios)}.",
                request=self.request, detalles=cambios,
            )
        return respuesta


class AprendizDeleteView(PersonalBienestarRequeridoMixin, DeleteView):
    """
    Elimina el Usuario completo (no solo la fila de Aprendiz) — si
    borráramos solo el perfil de Aprendiz, quedaría una cuenta de
    Usuario sin ningún perfil, y esa cuenta rota no podría volver a
    iniciar sesión (el mismo problema que arreglamos con los
    superusuarios sin Administrador).

    Si el aprendiz ya tiene horas de bienestar registradas, Django
    bloquea el borrado (HorasBienestar protege su Asistencia con
    on_delete=PROTECT, a propósito, para no perder ese historial) — en
    ese caso se avisa y se recomienda cambiar el estado a "Retirado" o
    "Egresado" en vez de eliminar.
    """
    model = Aprendiz
    success_url = reverse_lazy("usuarios:aprendices_lista")

    def get(self, request, *args, **kwargs):
        # Esta vista solo trabaja con POST (el botón de la lista pide la
        # confirmación con una ventana emergente). No tiene página propia:
        # antes, abrir esta dirección a mano daba un error 500 por falta de plantilla.
        return redirect(self.success_url)

    def form_valid(self, form):
        usuario = self.object.usuario
        quien = f"{usuario.get_full_name()} ({usuario.tipo_documento} {usuario.numero_documento})"

        try:
            usuario.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar: ya tiene horas de bienestar registradas "
                "(se protegen para no perder el historial). Puedes cambiar su "
                "estado a \"Retirado\" o \"Egresado\" en vez de eliminarlo."
            )
        else:
            messages.success(self.request, "Aprendiz eliminado.")
            auditar("aprendiz_eliminado", f"Se eliminó al aprendiz {quien}.", request=self.request)

        return redirect(self.success_url)
