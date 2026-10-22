"""
Exportaciones a Excel, Word y PDF de los catálogos y de los aprendices.
"""

from django.db.models import Count, Q

from core.services.exportar import responder_export
from usuarios.decorators import administrador_requerido, personal_bienestar_requerido
from usuarios.filters import AprendizFilter
from usuarios.models import Aprendiz, Grupo, Jornada, NivelFormacion, ProgramaFormacion
from usuarios.services.datos_aprendiz import DatosAprendiz, SELECT_RELATED_APRENDIZ


# ---------- Exportar catálogos (Excel / Word / PDF) ----------
# El helper que decide el formato vive en core/services/exportar.py
# (responder_export), compartido con eventos y publicaciones.

@administrador_requerido
def exportar_programas(request):
    programas = ProgramaFormacion.objects.select_related("nivel_formacion").order_by("nombre")

    q = request.GET.get("q", "").strip()
    if q:
        programas = programas.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))

    estado = request.GET.get("estado", "").strip()
    if estado:
        programas = programas.filter(estado=estado)

    encabezados = ["Nombre", "Código", "Nivel", "Duración (meses)", "Estado"]
    filas = [
        [p.nombre, p.codigo, p.nivel_formacion.nombre, p.duracion_meses, p.estado]
        for p in programas
    ]

    return responder_export(request, "programas_formacion", "Programas de formación", encabezados, filas, "usuarios:dashboard")


@administrador_requerido
def exportar_niveles(request):
    niveles = NivelFormacion.objects.annotate(total_programas=Count("programas")).order_by("nombre")

    q = request.GET.get("q", "").strip()
    if q:
        niveles = niveles.filter(nombre__icontains=q)

    encabezados = ["Nivel de formación", "Programas"]
    filas = [[n.nombre, n.total_programas] for n in niveles]

    return responder_export(request, "niveles_formacion", "Niveles de formación", encabezados, filas, "usuarios:dashboard")


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
def exportar_grupos(request):
    grupos = Grupo.objects.select_related("programa_formacion", "jornada").order_by("-fecha_creacion")

    programa_id = request.GET.get("programa_id")
    if programa_id:
        grupos = grupos.filter(programa_formacion_id=programa_id)

    jornada_id = request.GET.get("jornada_id")
    if jornada_id:
        grupos = grupos.filter(jornada_id=jornada_id)

    q = request.GET.get("q", "").strip()
    if q:
        grupos = grupos.filter(
            Q(numero_grupo__icontains=q) |
            Q(programa_formacion__nombre__icontains=q) |
            Q(jornada__nombre__icontains=q)
        )

    estado = request.GET.get("estado", "").strip()
    if estado:
        grupos = grupos.filter(estado=estado)

    encabezados = ["Número de grupo", "Programa", "Jornada", "Fecha inicio", "Fecha fin", "Estado"]
    filas = [
        [f.numero_grupo, f.programa_formacion.nombre, f.jornada.nombre, f.fecha_inicio, f.fecha_fin, f.estado]
        for f in grupos
    ]

    return responder_export(request, "grupos", "Grupos", encabezados, filas, "usuarios:dashboard")


@personal_bienestar_requerido
def exportar_aprendices(request):
    queryset = Aprendiz.objects.select_related(
        *SELECT_RELATED_APRENDIZ
    ).order_by("usuario__apellidos", "usuario__nombres")

    grupo_id = request.GET.get("grupo_id")
    if grupo_id:
        queryset = queryset.filter(grupo_id=grupo_id)

    # Mismo filtro que usa la tabla en pantalla (usuarios/filters.py) --
    # así "Exportar" nunca se puede desalinear de lo que se ve filtrado.
    aprendices = AprendizFilter(request.GET, queryset=queryset).qs

    # Los mismos datos que el listado de asistencia de los eventos
    # (usuarios/services/datos_aprendiz.py): una sola definición.
    encabezados = [*DatosAprendiz.ENCABEZADOS, "Estado"]
    filas = [
        [*DatosAprendiz.de(a).como_fila(), a.get_estado_display()]
        for a in aprendices
    ]

    return responder_export(request, "aprendices", "Aprendices", encabezados, filas, "usuarios:dashboard")
