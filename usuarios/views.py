from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin

from bienestar.models import HorasBienestar
from eventos.models import Inscripcion
from usuarios.forms import (
    LoginForm,
    RegistroAprendizForm,
    CrearUsuarioAdminForm,
    ProgramaFormacionForm,
    JornadaForm,
    FichaForm,
    AprendizEstadoForm,
)
from usuarios.decorators import administrador_requerido, personal_bienestar_requerido
from usuarios.filters import AprendizFilter
from usuarios.mixins import AdministradorRequeridoMixin, PersonalBienestarRequeridoMixin
from usuarios.models import Aprendiz, Ficha, Jornada, ProgramaFormacion
from usuarios.services import registrar_aprendiz, crear_usuario_administrativo
from usuarios.tables import AprendizTable
from core.services.exportar import responder_export


def fichas_por_programa(request):
    """
    Devuelve en JSON las fichas activas de un programa de formación.
    La usa el <select> de fichas del formulario de registro para
    filtrarse dinámicamente según el programa elegido.
    """

    programa_id = request.GET.get("programa_formacion")

    if not programa_id:
        return JsonResponse([], safe=False)

    fichas = Ficha.objects.filter(
        programa_formacion_id=programa_id,
        estado="activa"
    ).order_by("numero_ficha").values(
        "id", "numero_ficha", jornada_nombre=F("jornada__nombre")
    )

    return JsonResponse(list(fichas), safe=False)


def registro_aprendiz(request):

    if request.user.is_authenticated:
        return redirect("usuarios:dashboard")

    form = RegistroAprendizForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        usuario, aprendiz = registrar_aprendiz(
            tipo_documento=form.cleaned_data["tipo_documento"],
            numero_documento=form.cleaned_data["numero_documento"],
            nombres=form.cleaned_data["nombres"],
            apellidos=form.cleaned_data["apellidos"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            ficha=form.cleaned_data["ficha"],
        )

        login(request, usuario)
        messages.success(request, "¡Tu cuenta se creó correctamente! Bienvenido a Be Time.")
        return redirect("usuarios:dashboard")

    return render(request, "usuarios/registro.html", {"form": form})


@administrador_requerido
def crear_usuario_admin(request):
    """
    Un Administrador crea, desde el panel, cualquier tipo de cuenta:
    Aprendiz, Personal de Bienestar o incluso otro Administrador.
    A diferencia de registro_aprendiz, aquí la persona que llena el
    formulario NO es quien va a usar la cuenta -- por eso no hace
    login() al final, solo confirma que se creó.
    """

    form = CrearUsuarioAdminForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        usuario, perfil = crear_usuario_administrativo(
            tipo_documento=form.cleaned_data["tipo_documento"],
            numero_documento=form.cleaned_data["numero_documento"],
            nombres=form.cleaned_data["nombres"],
            apellidos=form.cleaned_data["apellidos"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            tipo_perfil=form.cleaned_data["tipo_perfil"],
            ficha=form.cleaned_data.get("ficha"),
            cargo=form.cleaned_data.get("cargo"),
        )

        messages.success(
            request,
            f"Cuenta creada correctamente para {usuario.get_full_name()} "
            f"({dict(form.fields['tipo_perfil'].choices)[form.cleaned_data['tipo_perfil']]})."
        )
        return redirect("usuarios:crear_usuario")

    return render(request, "usuarios/crear_usuario.html", {"form": form})


def login_view(request):

    if request.user.is_authenticated:
        return redirect("usuarios:dashboard")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        numero_documento = form.cleaned_data["numero_documento"]
        password = form.cleaned_data["password"]

        usuario = authenticate(
            request,
            username=numero_documento,
            password=password
        )

        if usuario is not None:
            login(request, usuario)
            return redirect("usuarios:dashboard")

        messages.error(request, "Documento o contraseña incorrectos.")

    # "acceso-personal/" es la misma vista y el mismo formulario que
    # "login/" -- lo único que cambia es que ahí no tiene sentido
    # mostrar los enlaces de "olvidé mi contraseña" / "crea tu cuenta
    # de aprendiz", pensados para aprendices, no para Bienestar/Admin.
    es_acceso_personal = request.resolver_match.url_name == "login_personal"

    return render(request, "usuarios/login.html", {
        "form": form,
        "es_acceso_personal": es_acceso_personal,
    })


def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("index")


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

    horas = HorasBienestar.objects.filter(
        asistencia__inscripcion__aprendiz=aprendiz
    ).select_related(
        "asistencia__inscripcion__evento"
    ).order_by("-fecha")

    total_horas = horas.aggregate(total=Sum("cantidad_horas"))["total"] or 0

    inscripciones = Inscripcion.objects.filter(
        aprendiz=aprendiz
    ).select_related("evento").order_by("-fecha_inscripcion")

    return render(request, "dashboard/aprendiz.html", {
        "aprendiz": aprendiz,
        "horas": horas,
        "total_horas": total_horas,
        "inscripciones": inscripciones,
    })


@login_required(login_url="usuarios:login")
def dashboard_bienestar(request):

    if not hasattr(request.user, "personal_bienestar"):
        return redirect("usuarios:dashboard")

    return render(request, "dashboard/bienestar.html", {
        "personal_bienestar": request.user.personal_bienestar,
    })


@login_required(login_url="usuarios:login")
def dashboard_admin(request):

    if not hasattr(request.user, "administrador"):
        return redirect("usuarios:dashboard")

    return render(request, "dashboard/admin.html", {
        "administrador": request.user.administrador,
    })


# ==========================================================
# Panel de catálogos: Programas de Formación, Jornadas,
# Fichas y Aprendices.
# ==========================================================

# ---------- Programas de Formación (solo Administrador) ----------

class ProgramaFormacionListView(AdministradorRequeridoMixin, ListView):
    model = ProgramaFormacion
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


class ProgramaFormacionDeleteView(AdministradorRequeridoMixin, DeleteView):
    model = ProgramaFormacion
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:programas_lista")
    extra_context = {
        "titulo_pagina": "Eliminar programa de formación",
        "url_cancelar": reverse_lazy("usuarios:programas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Programa de formación eliminado.")
        return super().form_valid(form)


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


class JornadaDeleteView(AdministradorRequeridoMixin, DeleteView):
    model = Jornada
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:jornadas_lista")
    extra_context = {
        "titulo_pagina": "Eliminar jornada",
        "url_cancelar": reverse_lazy("usuarios:jornadas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Jornada eliminada.")
        return super().form_valid(form)


# ---------- Fichas (Personal de Bienestar o Administrador) ----------
# La misma vista sirve para "todas las fichas" (panel/fichas/), para
# "las fichas de un programa" (panel/programas/<id>/fichas/) y para
# "las fichas de una jornada" (panel/jornadas/<id>/fichas/) — ver
# usuarios/urls.py. Si llega programa_id o jornada_id en la URL, se
# filtra y se agrega al contexto para la miga de pan y la exportación.

class FichaListView(PersonalBienestarRequeridoMixin, ListView):
    model = Ficha
    template_name = "usuarios/fichas_list.html"
    context_object_name = "fichas"
    paginate_by = 15

    def get_queryset(self):
        queryset = Ficha.objects.select_related(
            "programa_formacion", "jornada"
        ).order_by("-fecha_creacion")

        programa_id = self.kwargs.get("programa_id")
        if programa_id:
            queryset = queryset.filter(programa_formacion_id=programa_id)

        jornada_id = self.kwargs.get("jornada_id")
        if jornada_id:
            queryset = queryset.filter(jornada_id=jornada_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        programa_id = self.kwargs.get("programa_id")
        if programa_id:
            context["programa"] = get_object_or_404(ProgramaFormacion, pk=programa_id)
            context["export_extra_params"] = f"programa_id={programa_id}"

        jornada_id = self.kwargs.get("jornada_id")
        if jornada_id:
            context["jornada"] = get_object_or_404(Jornada, pk=jornada_id)
            context["export_extra_params"] = f"jornada_id={jornada_id}"

        return context


class FichaCreateView(PersonalBienestarRequeridoMixin, CreateView):
    model = Ficha
    form_class = FichaForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:fichas_lista")
    extra_context = {
        "titulo_pagina": "Crear ficha",
        "url_cancelar": reverse_lazy("usuarios:fichas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Ficha creada correctamente.")
        return super().form_valid(form)


class FichaUpdateView(PersonalBienestarRequeridoMixin, UpdateView):
    model = Ficha
    form_class = FichaForm
    template_name = "usuarios/panel_form.html"
    success_url = reverse_lazy("usuarios:fichas_lista")
    extra_context = {
        "titulo_pagina": "Editar ficha",
        "url_cancelar": reverse_lazy("usuarios:fichas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Ficha actualizada correctamente.")
        return super().form_valid(form)


class FichaDeleteView(PersonalBienestarRequeridoMixin, DeleteView):
    model = Ficha
    template_name = "usuarios/panel_confirmar_eliminar.html"
    success_url = reverse_lazy("usuarios:fichas_lista")
    extra_context = {
        "titulo_pagina": "Eliminar ficha",
        "url_cancelar": reverse_lazy("usuarios:fichas_lista"),
    }

    def form_valid(self, form):
        messages.success(self.request, "Ficha eliminada.")
        return super().form_valid(form)


# ---------- Aprendices (Personal de Bienestar o Administrador) ----------
# Se crean por auto-registro; aquí solo se consultan y se reasigna
# su ficha/estado (activo, retirado, egresado). No se crean ni se
# eliminan desde este panel.
#
# Igual que FichaListView: la misma vista sirve para "todos los
# aprendices" (panel/aprendices/) y para "los aprendices de una
# ficha" (panel/fichas/<id>/aprendices/).

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
            "usuario", "ficha", "ficha__programa_formacion"
        )

        ficha_id = self.kwargs.get("ficha_id")
        if ficha_id:
            queryset = queryset.filter(ficha_id=ficha_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ficha_id = self.kwargs.get("ficha_id")
        if ficha_id:
            context["ficha"] = get_object_or_404(
                Ficha.objects.select_related("programa_formacion"), pk=ficha_id
            )

        # Para que "Exportar" traiga lo mismo que se ve filtrado en
        # pantalla: como la búsqueda ahora es un <form method="get">
        # de verdad, la URL actual ya tiene ?q=...&estado=... — solo
        # hay que copiarlo (menos "page") al link de exportar. Además
        # de eso, si venimos filtrados por ficha (que es parte de la
        # URL, no un ?parametro=), lo agregamos aparte.
        parametros = self.request.GET.copy()
        parametros.pop("page", None)

        partes_extra = []
        if parametros:
            partes_extra.append(parametros.urlencode())
        if ficha_id:
            partes_extra.append(f"ficha_id={ficha_id}")

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

    def form_valid(self, form):
        messages.success(self.request, "Aprendiz actualizado correctamente.")
        return super().form_valid(form)


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

    def form_valid(self, form):
        usuario = self.object.usuario

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

        return redirect(self.success_url)


# ---------- Exportar catálogos (Excel / Word / PDF) ----------
# El helper que decide el formato vive en core/services/exportar.py
# (responder_export), compartido con eventos y publicaciones.

@administrador_requerido
def exportar_programas(request):
    programas = ProgramaFormacion.objects.order_by("nombre")

    q = request.GET.get("q", "").strip()
    if q:
        programas = programas.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))

    estado = request.GET.get("estado", "").strip()
    if estado:
        programas = programas.filter(estado=estado)

    encabezados = ["Nombre", "Código", "Nivel", "Duración (meses)", "Estado"]
    filas = [
        [p.nombre, p.codigo, p.nivel_formacion, p.duracion_meses, p.estado]
        for p in programas
    ]

    return responder_export(request, "programas_formacion", "Programas de formación", encabezados, filas, "usuarios:dashboard")


@administrador_requerido
def exportar_jornadas(request):
    jornadas = Jornada.objects.order_by("nombre")

    q = request.GET.get("q", "").strip()
    if q:
        jornadas = jornadas.filter(nombre__icontains=q)

    encabezados = ["Nombre"]
    filas = [[j.nombre] for j in jornadas]

    return responder_export(request, "jornadas", "Jornadas", encabezados, filas, "usuarios:dashboard")


@personal_bienestar_requerido
def exportar_fichas(request):
    fichas = Ficha.objects.select_related("programa_formacion", "jornada").order_by("-fecha_creacion")

    programa_id = request.GET.get("programa_id")
    if programa_id:
        fichas = fichas.filter(programa_formacion_id=programa_id)

    jornada_id = request.GET.get("jornada_id")
    if jornada_id:
        fichas = fichas.filter(jornada_id=jornada_id)

    q = request.GET.get("q", "").strip()
    if q:
        fichas = fichas.filter(
            Q(numero_ficha__icontains=q) |
            Q(programa_formacion__nombre__icontains=q) |
            Q(jornada__nombre__icontains=q)
        )

    estado = request.GET.get("estado", "").strip()
    if estado:
        fichas = fichas.filter(estado=estado)

    encabezados = ["Número de ficha", "Programa", "Jornada", "Fecha inicio", "Fecha fin", "Estado"]
    filas = [
        [f.numero_ficha, f.programa_formacion.nombre, f.jornada.nombre, f.fecha_inicio, f.fecha_fin, f.estado]
        for f in fichas
    ]

    return responder_export(request, "fichas", "Fichas", encabezados, filas, "usuarios:dashboard")


@personal_bienestar_requerido
def exportar_aprendices(request):
    queryset = Aprendiz.objects.select_related(
        "usuario", "ficha", "ficha__programa_formacion"
    ).order_by("usuario__apellidos", "usuario__nombres")

    ficha_id = request.GET.get("ficha_id")
    if ficha_id:
        queryset = queryset.filter(ficha_id=ficha_id)

    # Mismo filtro que usa la tabla en pantalla (usuarios/filters.py) --
    # así "Exportar" nunca se puede desalinear de lo que se ve filtrado.
    aprendices = AprendizFilter(request.GET, queryset=queryset).qs

    encabezados = ["Nombres", "Apellidos", "Tipo Documento", "Documento", "Ficha", "Programa", "Estado"]
    filas = [
        [
            a.usuario.nombres,
            a.usuario.apellidos,
            a.usuario.tipo_documento,
            a.usuario.numero_documento,
            a.ficha.numero_ficha,
            a.ficha.programa_formacion.nombre,
            a.estado,
        ]
        for a in aprendices
    ]

    return responder_export(request, "aprendices", "Aprendices", encabezados, filas, "usuarios:dashboard")
