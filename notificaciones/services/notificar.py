"""
Único lugar por donde se crean notificaciones. El resto del proyecto
(inscripciones, horas, cambios de evento, recordatorios) llama a estas
dos funciones y no toca el modelo directamente: si mañana se quiere
mandar también un correo o una notificación push, se cambia aquí.
"""

from notificaciones.models import Notificacion


def _recortar(texto, largo):
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def notificar(usuario, titulo, mensaje, *, url="", tipo="general"):
    """Crea una notificación para UN usuario (instancia de Usuario)."""
    return Notificacion.objects.create(
        usuario=usuario,
        titulo=_recortar(titulo, 150),
        mensaje=mensaje,
        url=url,
        tipo=tipo,
    )


def notificar_muchos(usuario_ids, titulo, mensaje, *, url="", tipo="general"):
    """
    Crea la misma notificación para muchos usuarios con UNA sola
    consulta (bulk_create). Recibe ids de Usuario. Devuelve cuántas creó.
    """
    ids = list(dict.fromkeys(usuario_ids))  # sin repetidos, conserva orden
    if not ids:
        return 0

    titulo = _recortar(titulo, 150)
    Notificacion.objects.bulk_create([
        Notificacion(usuario_id=uid, titulo=titulo, mensaje=mensaje, url=url, tipo=tipo)
        for uid in ids
    ])
    return len(ids)
