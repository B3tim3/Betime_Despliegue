from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from eventos.models import Inscripcion


@dataclass(frozen=True)
class FilaHistorial:
    """Una inscripción del aprendiz, lista para mostrar o exportar."""

    evento: str
    lugar: str
    fecha: datetime
    estado_codigo: str     # inscrito | asistio | no_asistio | cancelada | evento_cancelado
    estado: str            # texto para mostrar
    horas: int


def _estado(inscripcion):
    if inscripcion.evento.estado == "cancelado":
        return "evento_cancelado", "Evento cancelado"
    return inscripcion.estado, inscripcion.get_estado_display()


def historial_de(aprendiz):
    """
    Todas las inscripciones del aprendiz, de la más reciente a la más
    antigua, con su estado de asistencia y las horas que le dieron.

    Una sola consulta para las inscripciones y una para las horas
    (select_related + prefetch_related): el costo no crece con la cantidad
    de eventos. Las horas solo cuentan si la asistencia está en "asistió"
    (la misma regla de bienestar.services.progreso.horas_de).
    """
    inscripciones = (
        Inscripcion.objects.filter(aprendiz=aprendiz)
        .select_related("evento", "asistencia")
        .prefetch_related("asistencia__horas_bienestar")
        .order_by("-evento__fecha_inicio", "-id")
    )

    filas = []
    for ins in inscripciones:
        asistencia = getattr(ins, "asistencia", None)
        horas = 0
        if asistencia is not None and asistencia.asistio:
            horas = sum(h.cantidad_horas for h in asistencia.horas_bienestar.all())
        codigo, texto = _estado(ins)
        filas.append(FilaHistorial(
            evento=ins.evento.titulo,
            lugar=ins.evento.lugar,
            fecha=timezone.localtime(ins.evento.fecha_inicio),
            estado_codigo=codigo,
            estado=texto,
            horas=horas,
        ))
    return filas


def resumen_historial(filas):
    """Totales para las tarjetas de arriba. Las inscripciones canceladas no cuentan."""
    validas = [f for f in filas if f.estado_codigo not in ("cancelada", "evento_cancelado")]
    return {
        "inscritos": len(validas),
        "asistidos": sum(1 for f in validas if f.estado_codigo == "asistio"),
        "no_asistidos": sum(1 for f in validas if f.estado_codigo == "no_asistio"),
        "pendientes": sum(1 for f in validas if f.estado_codigo == "inscrito"),
        "horas": sum(f.horas for f in validas),
    }
