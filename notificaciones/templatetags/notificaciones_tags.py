from django import template

from notificaciones.models import Notificacion

register = template.Library()


@register.simple_tag(takes_context=True)
def notificaciones_no_leidas(context):
    """
    Cantidad de notificaciones sin leer del usuario logueado (0 si no
    hay sesión). Se guarda en el request para que, si la plantilla lo
    usa dos veces (campanita de celular y de escritorio), solo haga UNA
    consulta por página.

    Se hace con una etiqueta de plantilla -- y no con un context
    processor -- para no tener que tocar settings.py.
    """
    request = context.get("request")
    user = getattr(request, "user", None)

    if user is None or not user.is_authenticated:
        return 0

    if not hasattr(request, "_notificaciones_no_leidas"):
        request._notificaciones_no_leidas = Notificacion.objects.filter(
            usuario=user, leida=False
        ).count()

    return request._notificaciones_no_leidas
