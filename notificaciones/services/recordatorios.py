"""
Recordatorios de eventos: avisa (campanita + correo) a los aprendices
inscritos en eventos que empiezan pronto.

Cada inscripción se recuerda UNA sola vez (campo recordatorio_enviado),
así que es seguro ejecutar esto cada hora, cada día o varias veces al
día: nunca repite un aviso. Si el evento cambia de fecha, el campo se
reinicia (ver eventos/services/avisos.py) y el aprendiz recibe un
recordatorio nuevo para la fecha nueva.
"""

import logging
import os
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone

from eventos.models import Inscripcion
from eventos.services.estados import sincronizar_estados
from notificaciones.services import notificar

logger = logging.getLogger(__name__)

HORAS_POR_DEFECTO = 24


def _cuando(fecha):
    """'sábado 25/10/2026 a las 02:00 PM' en hora local."""
    local = timezone.localtime(fecha)
    return local.strftime("%d/%m/%Y a las %I:%M %p")


def _cuerpo_correo(inscripcion):
    evento = inscripcion.evento
    nombre = inscripcion.aprendiz.usuario.nombres
    sitio = os.environ.get("SITE_URL", "").rstrip("/")
    enlace = f"\n\nVer el evento: {sitio}/eventos/{evento.id}/" if sitio else ""
    horas = (
        f"\nHoras de bienestar que otorga: {evento.horas_otorgadas}"
        if evento.horas_otorgadas else ""
    )
    return (
        f"Hola, {nombre}.\n\n"
        f"Te recordamos que estás inscrito en el evento \"{evento.titulo}\".\n\n"
        f"Cuándo: {_cuando(evento.fecha_inicio)}\n"
        f"Dónde: {evento.lugar}"
        f"{horas}\n\n"
        f"Recuerda llevar tu código QR (lo encuentras en Be Time, en \"Mis inscripciones\") "
        f"para registrar tu asistencia. Si ya no puedes asistir, cancela tu inscripción "
        f"desde tu panel para liberar el cupo.{enlace}\n\n"
        f"— Bienestar al Aprendiz · Be Time"
    )


def enviar_recordatorios(horas=HORAS_POR_DEFECTO, ahora=None, enviar_correo=True):
    """
    Busca las inscripciones activas de eventos programados que empiezan
    dentro de las próximas `horas` horas y todavía no se han recordado.

    Devuelve un diccionario con el resumen:
      recordatorios: cuántas campanitas se crearon
      correos:       cuántos correos salieron
      sin_correo:    aprendices sin email registrado
      fallidos:      correos que fallaron (la campanita igual se creó)
    """
    ahora = ahora or timezone.now()
    limite = ahora + timedelta(hours=horas)
    sincronizar_estados(ahora)

    pendientes = list(
        Inscripcion.objects.filter(
            estado="inscrito",
            recordatorio_enviado=False,
            evento__estado="programado",
            evento__fecha_inicio__gt=ahora,
            evento__fecha_inicio__lte=limite,
        ).select_related("evento", "aprendiz__usuario").order_by("evento__fecha_inicio")
    )

    resumen = {"recordatorios": 0, "correos": 0, "sin_correo": 0, "fallidos": 0}
    if not pendientes:
        return resumen

    conexion = get_connection() if enviar_correo else None

    for insc in pendientes:
        evento = insc.evento
        usuario = insc.aprendiz.usuario

        notificar(
            usuario,
            f"Recordatorio: {evento.titulo}",
            f"Tu evento empieza el {_cuando(evento.fecha_inicio)} en {evento.lugar}. "
            f"Lleva tu código QR para registrar la asistencia.",
            url=f"/eventos/{evento.id}/",
            tipo="recordatorio",
        )
        resumen["recordatorios"] += 1

        if enviar_correo:
            if not usuario.email:
                resumen["sin_correo"] += 1
            else:
                try:
                    EmailMessage(
                        subject=f"Recordatorio: {evento.titulo}",
                        body=_cuerpo_correo(insc),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[usuario.email],
                        connection=conexion,
                    ).send()
                    resumen["correos"] += 1
                except Exception:
                    # Un correo caído no debe frenar a los demás ni repetir
                    # la campanita en la próxima corrida.
                    logger.exception("No se pudo enviar el recordatorio a %s", usuario.email)
                    resumen["fallidos"] += 1

        Inscripcion.objects.filter(pk=insc.pk).update(recordatorio_enviado=True)

    return resumen
