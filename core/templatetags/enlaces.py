"""
Template filter ``enlazar``: convierte URLs dentro de un texto plano
en enlaces ``<a>`` clicables.  El texto se escapa primero para evitar
XSS, y solo las URLs detectadas se convierten en etiquetas ``<a>``.

Uso en plantillas::

    {% load enlaces %}
    {{ publicacion.contenido|enlazar }}
"""

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# Patrón para detectar URLs (http, https, y sin protocolo)
_URL_RE = re.compile(
    r"("
    r"https?://[^\s<>\"')\]]+"   # URLs con protocolo
    r"|"
    r"www\.[^\s<>\"')\]]+"       # URLs con www sin protocolo
    r")",
    re.IGNORECASE,
)


@register.filter(name="enlazar", is_safe=True)
def enlazar(texto):
    """
    Recibe texto plano.  Escapa el HTML y convierte las URLs en
    enlaces ``<a href="..." target="_blank" rel="noopener">``.

    Se muestra solo el dominio + ruta corta como texto del enlace
    para que no se vean URLs larguísimas (como las de WhatsApp).
    """
    if not texto:
        return ""

    texto_escapado = escape(texto)

    def _reemplazar(match):
        url = match.group(0)
        href = url if url.startswith("http") else f"https://{url}"

        # Texto visible: dominio + inicio de la ruta (máx 40 chars)
        visible = url
        if len(visible) > 50:
            visible = visible[:47] + "..."

        return (
            f'<a href="{href}" target="_blank" rel="noopener noreferrer"'
            f' class="pub-enlace">{visible}</a>'
        )

    resultado = _URL_RE.sub(_reemplazar, texto_escapado)
    return mark_safe(resultado)
