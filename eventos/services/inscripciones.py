"""
Reglas de inscribirse y cancelar. Las usan las vistas del aprendiz
(detalle del evento y panel) para que haya UNA sola versión de la regla.
"""

import uuid

from django.db import transaction
from django.utils import timezone

from eventos.models import Evento, Inscripcion
from notificaciones.services import notificar


class InscripcionError(Exception):
    """Se puede mostrar tal cual al usuario (mensaje en español)."""


class CupoAgotadoError(InscripcionError):
    """El evento tiene cupo máximo y ya está completo."""


def motivo_no_confirmable(inscripcion):
    """
    Devuelve el mensaje (en español) de por qué NO se puede confirmar la
    asistencia de esta inscripción, o None si sí se puede.
    Solo lee datos: no cambia nada. Lo usan la pantalla del QR, el modo
    de escaneo rápido y las pruebas, para que la regla sea una sola.
    """
    # Sin límite de horario: quien se inscribió y asistió merece sus horas
    # sin importar cuándo se inscribió ni a qué hora se confirme.
    evento = inscripcion.evento

    if inscripcion.estado == "cancelada":
        return "Esta inscripción fue cancelada: el aprendiz ya no está inscrito en el evento."
    if evento.estado == "cancelado":
        return "El evento fue cancelado, no se puede confirmar asistencia."
    return None


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

    CUPO: si el evento tiene cupo máximo y ya está completo se lanza CupoAgotadoError
    (aplica también a quien quiere volver a inscribirse tras cancelar). Se bloquea la
    fila del evento mientras se cuenta y se inscribe, así dos personas que pulsan
    «Inscribirme» al mismo tiempo por el último lugar no pueden entrar las dos.
    """
    # Bloqueo por evento: las inscripciones al MISMO evento se atienden de a una.
    evento = Evento.objects.select_for_update().get(pk=evento.pk)

    if evento.estado_actual != "programado":
        raise InscripcionError("Este evento ya no está abierto para inscripciones.")

    inscripcion = Inscripcion.objects.filter(evento=evento, aprendiz=aprendiz).first()

    if inscripcion is not None and inscripcion.estado != "cancelada":
        return inscripcion, "existente"          # ya tenía su lugar: no consume otro

    if evento.esta_lleno:
        raise CupoAgotadoError(
            f"Los cupos de este evento se agotaron ({evento.cupo_maximo} de {evento.cupo_maximo}). "
            "Si alguien cancela, el lugar se libera y podrás inscribirte."
        )

    if inscripcion is None:
        inscripcion = Inscripcion.objects.create(evento=evento, aprendiz=aprendiz, estado="inscrito")
        accion = "creada"
    else:
        inscripcion.estado = "inscrito"
        inscripcion.token = uuid.uuid4()
        inscripcion.recordatorio_enviado = False
        inscripcion.save(update_fields=["estado", "token", "recordatorio_enviado"])
        accion = "reactivada"

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
