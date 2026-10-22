"""
Reglas de inscribirse y cancelar. Las usan las vistas del aprendiz
(detalle del evento y panel) para que haya UNA sola versión de la regla.
"""

import uuid

from django.db import transaction
from django.utils import timezone

from eventos.models import Inscripcion
from notificaciones.services import notificar


class InscripcionError(Exception):
    """Se puede mostrar tal cual al usuario (mensaje en español)."""


def _fecha(evento):
    return timezone.localtime(evento.fecha_inicio).strftime("%d/%m/%Y a las %I:%M %p")


@transaction.atomic
def inscribir(aprendiz, evento):
    """
    Inscribe al aprendiz. Devuelve (inscripcion, accion) con accion en
    "creada", "reactivada" (tenía una inscripción cancelada y la retoma)
    o "existente" (ya estaba inscrito: no se hace nada).

    Al reactivar se genera un token nuevo: el QR anterior, que ya había
    sido cancelado, deja de servir.
    """
    if evento.estado != "programado":
        raise InscripcionError("Este evento ya no está abierto para inscripciones.")

    inscripcion, creada = Inscripcion.objects.select_for_update().get_or_create(
        evento=evento, aprendiz=aprendiz, defaults={"estado": "inscrito"},
    )

    if creada:
        accion = "creada"
    elif inscripcion.estado == "cancelada":
        inscripcion.estado = "inscrito"
        inscripcion.token = uuid.uuid4()
        inscripcion.recordatorio_enviado = False
        inscripcion.save(update_fields=["estado", "token", "recordatorio_enviado"])
        accion = "reactivada"
    else:
        return inscripcion, "existente"

    notificar(
        aprendiz.usuario,
        f"Inscripción confirmada: {evento.titulo}",
        f"Quedaste inscrito el {_fecha(evento)} en {evento.lugar}. "
        f"Tu código QR está en \"Mis inscripciones\".",
        url=f"/eventos/{evento.id}/",
        tipo="inscripcion",
    )
    return inscripcion, accion


@transaction.atomic
def cancelar(inscripcion):
    """Cancela una inscripción activa (ver Inscripcion.puede_cancelarse)."""
    if inscripcion.estado != "inscrito":
        raise InscripcionError("Esta inscripción no está activa, así que no se puede cancelar.")
    if not inscripcion.puede_cancelarse:
        raise InscripcionError(
            "Ya no puedes cancelar esta inscripción porque el evento ya comenzó o ya no está programado."
        )

    inscripcion.estado = "cancelada"
    inscripcion.save(update_fields=["estado"])

    evento = inscripcion.evento
    notificar(
        inscripcion.aprendiz.usuario,
        f"Inscripción cancelada: {evento.titulo}",
        "Cancelaste tu inscripción. Si cambias de opinión, puedes volver a inscribirte "
        "mientras el evento siga abierto.",
        url=f"/eventos/{evento.id}/",
        tipo="cancelacion",
    )
    return inscripcion
