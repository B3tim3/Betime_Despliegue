from django import template

from core.services.imagenes import nombre_mini

register = template.Library()


@register.filter
def miniatura(archivo):
    """
    URL de la miniatura de una imagen (para listados y tarjetas). Las imágenes que ya
    pasaron por la optimización (.webp) tienen miniatura; las antiguas devuelven la
    original, así nada se rompe mientras se procesan con `optimizar_imagenes`.
    Sin consultas ni acceso al disco: la miniatura se deduce del nombre.
    """
    if not archivo:
        return ""
    nombre = archivo.name or ""
    if nombre.lower().endswith(".webp") and not nombre.lower().endswith("_mini.webp"):
        return archivo.storage.url(nombre_mini(nombre))
    return archivo.url
