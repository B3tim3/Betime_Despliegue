"""
Servicios de bienestar — lógica que toca más de un modelo a la vez,
igual que usuarios/services/registro.py.
"""

from django.db import transaction

from bienestar.models import HorasBienestar
from core.services.auditoria import registrar as auditar
from eventos.models import Asistencia
from notificaciones.services import notificar


@transaction.atomic
def registrar_asistencia_y_horas(*, inscripcion, asistio, cantidad_horas, motivo, asignado_por, metodo="checklist"):
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

    asistio_antes = Asistencia.objects.filter(inscripcion=inscripcion).values_list("asistio", flat=True).first()
    horas_antes = HorasBienestar.objects.filter(
        asistencia__inscripcion=inscripcion
    ).values_list("cantidad_horas", flat=True).first()

    asistencia, _ = Asistencia.objects.update_or_create(
        inscripcion=inscripcion,
        defaults={"asistio": asistio},
    )

    inscripcion.estado = "asistio" if asistio else "no_asistio"
    inscripcion.save(update_fields=["estado"])

    if asistio and cantidad_horas:
        previas = HorasBienestar.objects.filter(asistencia=asistencia).values_list(
            "cantidad_horas", flat=True
        ).first()

        HorasBienestar.objects.update_or_create(
            asistencia=asistencia,
            defaults={
                "cantidad_horas": cantidad_horas,
                "motivo": motivo,
                "asignado_por": asignado_por,
            },
        )

        # Avisar solo si las horas son nuevas o cambiaron: guardar el
        # checklist dos veces con lo mismo no debe llenar la campanita.
        if previas != cantidad_horas:
            evento = inscripcion.evento
            notificar(
                inscripcion.aprendiz.usuario,
                f"Se registraron {cantidad_horas} hora{'s' if cantidad_horas != 1 else ''} de bienestar",
                f"Por tu asistencia a «{evento.titulo}». Puedes verlas en tu historial.",
                url="/bienestar/mi-historial/",
                tipo="horas",
            )

    # Bitácora: solo si algo cambió (guardar el checklist completo de nuevo no
    # debe llenarla con cien registros iguales).
    horas_ahora = cantidad_horas if (asistio and cantidad_horas) else horas_antes
    if asistio_antes is None or asistio_antes != asistio or horas_antes != horas_ahora:
        aprendiz = inscripcion.aprendiz.usuario
        auditar(
            "asistencia",
            f"{'Asistió' if asistio else 'No asistió'}: {aprendiz.get_full_name()} "
            f"({aprendiz.numero_documento}) al evento «{inscripcion.evento.titulo}»"
            + (f", {horas_ahora} horas." if asistio and horas_ahora else "."),
            usuario=asignado_por.usuario,
            detalles={
                "inscripcion_id": inscripcion.pk, "asistio": asistio, "metodo": metodo,
                "horas_antes": horas_antes, "horas_ahora": horas_ahora,
            },
        )

    return asistencia
