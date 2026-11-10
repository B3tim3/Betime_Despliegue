"""
Catálogos de formación: programas, niveles, jornadas y grupos (listar, crear, editar, eliminar).
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.services.auditoria import registrar as auditar
from usuarios.forms import (
    GrupoForm,
    JornadaForm,
    NivelFormacionForm,
    ProgramaFormacionForm,
)
from usuarios.mixins import AdministradorRequeridoMixin, PersonalBienestarRequeridoMixin
from usuarios.models import Grupo, Jornada, NivelFormacion, ProgramaFormacion
from usuarios.services.grupos import filtrar_grupos


# ==========================================================
# Panel de catálogos: Programas de Formación, Jornadas,
# Grupos y Aprendices.
# ==========================================================

class EliminarProtegidoMixin:
    """
    Para las vistas de eliminar de los catálogos. Las relaciones entre
    catálogos son PROTECT a propósito (no se puede borrar un programa
    que tiene grupos, ni un grupo que tiene aprendices, etc.). Sin este
    mixin, intentarlo hacía fallar la página con un error 500; ahora se
    avisa con un mensaje y se vuelve al listado.
    """

    mensaje_eliminado = "Eliminado correctamente."
    mensaje_protegido = "No se puede eliminar: todavía tiene registros asociados."

    def form_valid(self, form):
        descripcion = f"{self.object._meta.verbose_name}: {self.object}"
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(self.request, self.mensaje_protegido)
        else:
            messages.success(self.request, self.mensaje_eliminado)
            auditar("catalogo_eliminado", f"Se eliminó {descripcion}.", request=self.request)

        return redirect(self.get_success_url())


# ---------- Programas de Formación (solo Administrador) ----------

class ProgramaFormacionListView(AdministradorRequeridoMixin, ListView):
    model = ProgramaFormacion
    queryset = ProgramaFormacion.objects.select_related("nivel_formacion")
    template_name = "usuarios/programas_list.html"
    context_object_name = "programas"
    ordering = ["nombre"]
    paginate_by = 15


class ProgramaFormacionCreateView(AdministradorRequeridoMixin, CreateView):
    model = ProgramaFormacion
    form_class = ProgramaFormacionForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:programas_lista")
    extra_context = {
        "titulo_pagina": "Crear programa de formación",
        "url_cancelar": reverse_lazy("usuarios:programas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Programa de formación creado correctamente.")
        return super().form_valid(form)


class ProgramaFormacionUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = ProgramaFormacion
    form_class = ProgramaFormacionForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:programas_lista")
    extra_context = {
        "titulo_pagina": "Editar programa de formación",
        "url_cancelar": reverse_lazy("usuarios:programas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Programa de formación actualizado correctamente.")
        return super().form_valid(form)


class ProgramaFormacionDeleteView(EliminarProtegidoMixin, AdministradorRequeridoMixin, DeleteView):
    model = ProgramaFormacion
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:programas_lista")
    extra_context = {
        "titulo_pagina": "Eliminar programa de formación",
        "url_cancelar": reverse_lazy("usuarios:programas_lista"),
    }
    mensaje_eliminado = "Programa de formación eliminado."
    mensaje_protegido = (
        "No se puede eliminar: el programa tiene grupos registrados. Elimina o reasigna esos grupos primero."
    )


# ---------- Niveles de formación (solo Administrador) ----------
# Catálogo editable: el Administrador agrega, edita y quita niveles
# (Técnico, Tecnólogo, ...) y los programas eligen uno de ellos.

class NivelFormacionListView(AdministradorRequeridoMixin, ListView):
    model = NivelFormacion
    template_name = "usuarios/niveles_list.html"
    context_object_name = "niveles"
    paginate_by = 15

    def get_queryset(self):
        return NivelFormacion.objects.annotate(
            total_programas=Count("programas")
        ).order_by("nombre")


class NivelFormacionCreateView(AdministradorRequeridoMixin, CreateView):
    model = NivelFormacion
    form_class = NivelFormacionForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:niveles_lista")
    extra_context = {
        "titulo_pagina": "Crear nivel de formación",
        "url_cancelar": reverse_lazy("usuarios:niveles_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Nivel de formación creado correctamente.")
        return super().form_valid(form)


class NivelFormacionUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = NivelFormacion
    form_class = NivelFormacionForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:niveles_lista")
    extra_context = {
        "titulo_pagina": "Editar nivel de formación",
        "url_cancelar": reverse_lazy("usuarios:niveles_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Nivel de formación actualizado correctamente.")
        return super().form_valid(form)


class NivelFormacionDeleteView(EliminarProtegidoMixin, AdministradorRequeridoMixin, DeleteView):
    """
    Un nivel que todavía tiene programas no se puede eliminar (la
    relación es PROTECT): se avisa con un mensaje en vez de dejar que
    la página falle con un error 500.
    """
    model = NivelFormacion
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:niveles_lista")
    extra_context = {
        "titulo_pagina": "Eliminar nivel de formación",
        "url_cancelar": reverse_lazy("usuarios:niveles_lista"),
    }
    mensaje_eliminado = "Nivel de formación eliminado."
    mensaje_protegido = (
        "No se puede eliminar: hay programas de formación que usan este nivel. Cambia el nivel de esos programas primero."
    )


# ---------- Jornadas (solo Administrador) ----------

class JornadaListView(AdministradorRequeridoMixin, ListView):
    model = Jornada
    template_name = "usuarios/jornadas_list.html"
    context_object_name = "jornadas"
    ordering = ["nombre"]
    paginate_by = 15


class JornadaCreateView(AdministradorRequeridoMixin, CreateView):
    model = Jornada
    form_class = JornadaForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:jornadas_lista")
    extra_context = {
        "titulo_pagina": "Crear jornada",
        "url_cancelar": reverse_lazy("usuarios:jornadas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Jornada creada correctamente.")
        return super().form_valid(form)


class JornadaUpdateView(AdministradorRequeridoMixin, UpdateView):
    model = Jornada
    form_class = JornadaForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:jornadas_lista")
    extra_context = {
        "titulo_pagina": "Editar jornada",
        "url_cancelar": reverse_lazy("usuarios:jornadas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Jornada actualizada correctamente.")
        return super().form_valid(form)


class JornadaDeleteView(EliminarProtegidoMixin, AdministradorRequeridoMixin, DeleteView):
    model = Jornada
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:jornadas_lista")
    extra_context = {
        "titulo_pagina": "Eliminar jornada",
        "url_cancelar": reverse_lazy("usuarios:jornadas_lista"),
    }
    mensaje_eliminado = "Jornada eliminada."
    mensaje_protegido = (
        "No se puede eliminar: hay grupos que usan esta jornada. Elimina o reasigna esos grupos primero."
    )


# ---------- Grupos (Personal de Bienestar o Administrador) ----------
# La misma vista sirve para "todos los grupos" (panel/grupos/), para
# "los grupos de un programa" (panel/programas/<id>/grupos/) y para
# "los grupos de una jornada" (panel/jornadas/<id>/grupos/) — ver
# usuarios/urls.py. Si llega programa_id o jornada_id en la URL, se
# filtra y se agrega al contexto para la miga de pan y la exportación.

class GrupoListView(PersonalBienestarRequeridoMixin, ListView):
    """
    Dos pestañas para que la lista de trabajo siga corta con los años:
      · Vigentes (por defecto): grupos que no se han cerrado y cuya fecha de fin no pasó.
      · Historial: los que terminaron o se cerraron, con búsqueda, año y paginación.
    """
    model = Grupo
    template_name = "usuarios/grupos_list.html"
    context_object_name = "grupos"
    paginate_by = 15

    def get_queryset(self):
        grupos, self.vista = filtrar_grupos(
            self.request.GET,
            programa_id=self.kwargs.get("programa_id"),
            jornada_id=self.kwargs.get("jornada_id"),
        )
        return grupos

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        programa_id = self.kwargs.get("programa_id")
        jornada_id = self.kwargs.get("jornada_id")

        base = Grupo.objects.all()
        if programa_id:
            base = base.filter(programa_formacion_id=programa_id)
        if jornada_id:
            base = base.filter(jornada_id=jornada_id)

        historial = base.historial()
        context["vista"] = self.vista
        context["total_vigentes"] = base.vigentes().count()
        context["total_historial"] = historial.count()
        context["anios"] = sorted(
            {f.year for f in historial.dates("fecha_fin", "year")}, reverse=True
        )
        context["q"] = (params.get("q") or "").strip()
        context["anio"] = params.get("anio", "")
        context["estado_filtro"] = params.get("estado", "")

        # Para que la paginación y la exportación conserven pestaña, búsqueda y año.
        filtros = {"vista": self.vista, "q": context["q"]}
        if self.vista == "historial":
            filtros["anio"] = context["anio"]
            filtros["estado"] = context["estado_filtro"]
        filtros = {k: v for k, v in filtros.items() if v}
        context["extra_query"] = ("&" + urlencode(filtros)) if filtros else ""

        extra = []
        if programa_id:
            context["programa"] = get_object_or_404(ProgramaFormacion, pk=programa_id)
            extra.append(f"programa_id={programa_id}")
        if jornada_id:
            context["jornada"] = get_object_or_404(Jornada, pk=jornada_id)
            extra.append(f"jornada_id={jornada_id}")
        if filtros:
            extra.append(urlencode(filtros))
        context["export_extra_params"] = "&".join(extra)
        return context


class GrupoCreateView(PersonalBienestarRequeridoMixin, CreateView):
    model = Grupo
    form_class = GrupoForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:grupos_lista")
    extra_context = {
        "titulo_pagina": "Crear grupo",
        "url_cancelar": reverse_lazy("usuarios:grupos_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Grupo creado correctamente.")
        return super().form_valid(form)


class GrupoUpdateView(PersonalBienestarRequeridoMixin, UpdateView):
    model = Grupo
    form_class = GrupoForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:grupos_lista")
    extra_context = {
        "titulo_pagina": "Editar grupo",
        "url_cancelar": reverse_lazy("usuarios:grupos_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Grupo actualizado correctamente.")
        return super().form_valid(form)


class GrupoDeleteView(EliminarProtegidoMixin, PersonalBienestarRequeridoMixin, DeleteView):
    model = Grupo
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:grupos_lista")
    extra_context = {
        "titulo_pagina": "Eliminar grupo",
        "url_cancelar": reverse_lazy("usuarios:grupos_lista"),
    }
    mensaje_eliminado = "Grupo eliminado."
    mensaje_protegido = (
        "No se puede eliminar: el grupo tiene aprendices registrados. Reasigna a los aprendices a otro grupo primero."
    )
