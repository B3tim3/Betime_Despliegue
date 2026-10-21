"""
Avisos a los aprendices cuando Bienestar crea, cambia o elimina un evento.
Todos usan una sola consulta para crear las notificaciones (bulk_create).
"""

from django.utils import timezone

from eventos.models import Inscripcion
from notificaciones.services import notificar_muchos
from usuarios.models import Usuario


def _fecha(dt):
    return timezone.localtime(dt).strftime("%d/%m/%Y %I:%M %p")


def _usuarios_inscritos(evento):
    return list(
        Inscripcion.objects.filter(evento=evento, estado="inscrito")
        .values_list("aprendiz__usuario_id", flat=True)
    )


def avisar_evento_nuevo(evento):
    """Avisa a todos los aprendices activos que hay un evento nuevo abierto."""
    if evento.estado != "programado":
        return 0
    ids = Usuario.objects.filter(aprendiz__isnull=False, is_active=True).values_list("id", flat=True)
    return notificar_muchos(
        ids,
        f"Nuevo evento: {evento.titulo}",
        f"{_fecha(evento.fecha_inicio)} · {evento.lugar}"
        + (f" · {evento.horas_otorgadas} horas de bienestar" if evento.horas_otorgadas else ""),
        url=f"/eventos/{evento.id}/",
        tipo="evento",
    )


def avisar_cambios_evento(anterior, evento):
    """
    Compara el evento como estaba (`anterior`) con como quedó y avisa a
    los inscritos si cambió algo que les afecta: cancelación, fecha o lugar.
    """
    inscritos = _usuarios_inscritos(evento)
    url = f"/eventos/{evento.id}/"

    def minuto(dt):  # el formulario trabaja al minuto: ignorar segundos
        return dt.replace(second=0, microsecond=0)

    cancelado = anterior.estado != "cancelado" and evento.estado == "cancelado"
    cambio_fecha = (
        minuto(anterior.fecha_inicio) != minuto(evento.fecha_inicio)
        or minuto(anterior.fecha_fin) != minuto(evento.fecha_fin)
    )
    cambio_lugar = anterior.lugar != evento.lugar

    if cambio_fecha:
        # Con fecha nueva, el recordatorio anterior ya no vale: que le llegue otro.
        Inscripcion.objects.filter(evento=evento, estado="inscrito").update(recordatorio_enviado=False)

    if cancelado:
        return notificar_muchos(
            inscritos, f"Evento cancelado: {evento.titulo}",
            "Bienestar canceló este evento. Tu inscripción ya no tiene efecto.",
            url=url, tipo="cancelacion",
        )

    cambios = []
    if cambio_fecha:
        cambios.append(f"nueva fecha: {_fecha(evento.fecha_inicio)}")
    if cambio_lugar:
        cambios.append(f"nuevo lugar: {evento.lugar}")
    if not cambios:
        return 0

    return notificar_muchos(
        inscritos, f"Cambió el evento: {evento.titulo}",
        "Atención, " + " · ".join(cambios) + ".",
        url=url, tipo="evento",
    )


def avisar_evento_eliminado(evento):
    """Se llama ANTES de borrar el evento (después ya no hay inscripciones)."""
    if evento.fecha_fin <= timezone.now():
        return 0  # evento pasado: no tiene sentido avisar
    return notificar_muchos(
        _usuarios_inscritos(evento), f"Evento eliminado: {evento.titulo}",
        "Bienestar eliminó este evento. Tu inscripción ya no tiene efecto.",
        url="", tipo="cancelacion",
    )
