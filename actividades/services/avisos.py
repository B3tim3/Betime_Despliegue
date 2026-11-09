"""
Avisos a los aprendices cuando Bienestar crea, cambia o elimina una actividad.
Todos usan una sola consulta para crear las notificaciones (bulk_create).
"""

from django.utils import timezone

from actividades.models import Inscripcion
from notificaciones.services import notificar_muchos
from usuarios.models import Usuario


def _fecha(dt):
    return timezone.localtime(dt).strftime("%d/%m/%Y %I:%M %p")


def _usuarios_inscritos(actividad):
    return list(
        Inscripcion.objects.filter(actividad=actividad, estado="inscrito")
        .values_list("aprendiz__usuario_id", flat=True)
    )


def avisar_actividad_nuevo(actividad):
    """Avisa a todos los aprendices activos que hay una actividad nuevo abierto."""
    if actividad.estado != "programado":
        return 0
    ids = Usuario.objects.filter(aprendiz__isnull=False, is_active=True).values_list("id", flat=True)
    return notificar_muchos(
        ids,
        f"Nueva actividad: {actividad.titulo}",
        f"{_fecha(actividad.fecha_inicio)} · {actividad.lugar}"
        + (f" · {actividad.horas_otorgadas} horas de bienestar" if actividad.horas_otorgadas else ""),
        url=f"/actividades/{actividad.id}/",
        tipo="actividad",
    )


def avisar_cambios_actividad(anterior, actividad):
    """
    Compara la actividad como estaba (`anterior`) con como quedó y avisa a
    los inscritos si cambió algo que les afecta: cancelación, fecha o lugar.
    """
    inscritos = _usuarios_inscritos(actividad)
    url = f"/actividades/{actividad.id}/"

    def minuto(dt):  # el formulario trabaja al minuto: ignorar segundos
        return dt.replace(second=0, microsecond=0)

    cancelado = anterior.estado != "cancelado" and actividad.estado == "cancelado"
    cambio_fecha = (
        minuto(anterior.fecha_inicio) != minuto(actividad.fecha_inicio)
        or minuto(anterior.fecha_fin) != minuto(actividad.fecha_fin)
    )
    cambio_lugar = anterior.lugar != actividad.lugar

    if cambio_fecha:
        # Con fecha nueva, el recordatorio anterior ya no vale: que le llegue otro.
        Inscripcion.objects.filter(actividad=actividad, estado="inscrito").update(recordatorio_enviado=False)

    if cancelado:
        return notificar_muchos(
            inscritos, f"Actividad cancelada: {actividad.titulo}",
            "Bienestar canceló esta actividad. Tu inscripción ya no tiene efecto.",
            url=url, tipo="cancelacion",
        )

    cambios = []
    if cambio_fecha:
        cambios.append(f"nueva fecha: {_fecha(actividad.fecha_inicio)}")
    if cambio_lugar:
        cambios.append(f"nuevo lugar: {actividad.lugar}")
    if not cambios:
        return 0

    return notificar_muchos(
        inscritos, f"Cambió la actividad: {actividad.titulo}",
        "Atención, " + " · ".join(cambios) + ".",
        url=url, tipo="actividad",
    )


def avisar_actividad_eliminado(actividad):
    """Se llama ANTES de borrar la actividad (después ya no hay inscripciones)."""
    if actividad.fecha_fin <= timezone.now():
        return 0  # actividad pasado: no tiene sentido avisar
    return notificar_muchos(
        _usuarios_inscritos(actividad), f"Actividad eliminada: {actividad.titulo}",
        "Bienestar eliminó esta actividad. Tu inscripción ya no tiene efecto.",
        url="", tipo="cancelacion",
    )
