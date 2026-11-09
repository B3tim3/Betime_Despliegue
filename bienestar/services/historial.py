from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from actividades.models import Inscripcion


@dataclass(frozen=True)
class FilaHistorial:
    """Una inscripción del aprendiz, lista para mostrar o exportar."""

    actividad: str
    lugar: str
    fecha: datetime
    estado_codigo: str     # inscrito | asistio | no_asistio | cancelada | actividad_cancelado
    estado: str            # texto para mostrar
    horas: int


@dataclass(frozen=True)
class FilaExtracurricular:
    """Una actividad por mérito del aprendiz (horas fuera de actividades)."""

    actividad: str
    fecha: object          # datetime.date
    estado_codigo: str     # otorgada | pendiente
    estado: str
    horas: int


def historial_extracurricular_de(aprendiz):
    """Actividades por mérito en las que participó, de la más reciente a la más antigua."""
    participaciones = (
        aprendiz.participaciones_extracurriculares
        .select_related("actividad", "horas")
        .order_by("-actividad__fecha", "-id")
    )
    filas = []
    for p in participaciones:
        otorgada = p.estado == "otorgada"
        registro = getattr(p, "horas", None)
        filas.append(FilaExtracurricular(
            actividad=p.actividad.titulo,
            fecha=p.actividad.fecha,
            estado_codigo=p.estado,
            estado="Horas otorgadas" if otorgada else "Pendiente de horas",
            horas=registro.cantidad_horas if (otorgada and registro) else 0,
        ))
    return filas


def _estado(inscripcion):
    if inscripcion.actividad.estado == "cancelado":
        return "actividad_cancelado", "Actividad cancelada"
    return inscripcion.estado, inscripcion.get_estado_display()


def historial_de(aprendiz):
    """
    Todas las inscripciones del aprendiz, de la más reciente a la más
    antigua, con su estado de asistencia y las horas que le dieron.

    Una sola consulta para las inscripciones y una para las horas
    (select_related + prefetch_related): el costo no crece con la cantidad
    de actividades. Las horas solo cuentan si la asistencia está en "asistió"
    (la misma regla de bienestar.services.progreso.horas_de).
    """
    inscripciones = (
        Inscripcion.objects.filter(aprendiz=aprendiz)
        .select_related("actividad", "asistencia")
        .prefetch_related("asistencia__horas_bienestar")
        .order_by("-actividad__fecha_inicio", "-id")
    )

    filas = []
    for ins in inscripciones:
        asistencia = getattr(ins, "asistencia", None)
        horas = 0
        if asistencia is not None and asistencia.asistio:
            horas = sum(h.cantidad_horas for h in asistencia.horas_bienestar.all())
        codigo, texto = _estado(ins)
        filas.append(FilaHistorial(
            actividad=ins.actividad.titulo,
            lugar=ins.actividad.lugar,
            fecha=timezone.localtime(ins.actividad.fecha_inicio),
            estado_codigo=codigo,
            estado=texto,
            horas=horas,
        ))
    return filas


def resumen_historial(filas):
    """Totales para las tarjetas de arriba. Las inscripciones canceladas no cuentan."""
    validas = [f for f in filas if f.estado_codigo not in ("cancelada", "actividad_cancelado")]
    return {
        "inscritos": len(validas),
        "asistidos": sum(1 for f in validas if f.estado_codigo == "asistio"),
        "no_asistidos": sum(1 for f in validas if f.estado_codigo == "no_asistio"),
        "pendientes": sum(1 for f in validas if f.estado_codigo == "inscrito"),
        "horas": sum(f.horas for f in validas),
    }
