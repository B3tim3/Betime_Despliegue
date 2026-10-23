"""
Único punto de entrada para escribir en la bitácora de auditoría.

    registrar("meta_horas", "Cambió la meta de 40 a 60 horas", request=request,
              detalles={"antes": 40, "despues": 60})

Reglas: nunca pongas contraseñas ni datos que no hagan falta en `detalles`.
"""

from core.models import RegistroAuditoria


def _ip(request):
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return reenviada or request.META.get("REMOTE_ADDR") or None


def registrar(accion, descripcion, *, request=None, usuario=None, detalles=None):
    """
    `usuario` es quien hizo la acción; si no se pasa y hay `request`, se toma
    de la sesión. Puede quedar vacío (por ejemplo, un intento de acceso de
    alguien que no inició sesión).
    """
    if usuario is None and request is not None and request.user.is_authenticated:
        usuario = request.user

    texto = ""
    if usuario is not None:
        texto = f"{usuario.get_full_name()} ({usuario.tipo_documento} {usuario.numero_documento})"

    return RegistroAuditoria.objects.create(
        usuario=usuario,
        usuario_texto=texto,
        accion=accion,
        descripcion=descripcion,
        detalles=detalles or {},
        ip=_ip(request) if request is not None else None,
    )
