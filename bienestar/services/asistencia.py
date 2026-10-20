"""
Servicios de bienestar — lógica que toca más de un modelo a la vez,
igual que usuarios/services/registro.py.
"""

from django.db import transaction

from bienestar.models import HorasBienestar
from eventos.models import Asistencia


@transaction.atomic
def registrar_asistencia_y_horas(*, inscripcion, asistio, cantidad_horas, motivo, asignado_por):
    """
    Registra (o actualiza) la Asistencia de una Inscripción, y si
    asistió, le asigna (o corrige) las horas de bienestar
    correspondientes.

    Es seguro llamar esto más de una vez para la misma inscripción: no
    crea una segunda Asistencia ni un segundo registro de horas — si
    ya existían, los actualiza con los valores nuevos (por ejemplo, si
    Bienestar vuelve a guardar el checklist con una cantidad de horas
    distinta a la primera vez).
    """

    asistencia, _ = Asistencia.objects.update_or_create(
        inscripcion=inscripcion,
        defaults={"asistio": asistio},
    )

    inscripcion.estado = "asistio" if asistio else "no_asistio"
    inscripcion.save(update_fields=["estado"])

    if asistio and cantidad_horas:
        HorasBienestar.objects.update_or_create(
            asistencia=asistencia,
            defaults={
                "cantidad_horas": cantidad_horas,
                "motivo": motivo,
                "asignado_por": asignado_por,
            },
        )

    return asistencia
