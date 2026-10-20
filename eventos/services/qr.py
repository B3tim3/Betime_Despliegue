"""
Generación de códigos QR para las inscripciones a eventos.

El QR de cada inscripción codifica una URL completa (no solo el
token) -- así se puede escanear con la app de cámara nativa de
cualquier celular, sin necesitar tener Be Time abierto para nada.
"""

from io import BytesIO


def generar_imagen_qr(contenido):
    """
    Genera un código QR en memoria (PNG) a partir de un texto o URL.
    Devuelve un BytesIO listo para usar en una HttpResponse o guardar.
    """
    import qrcode

    imagen = qrcode.make(contenido, box_size=8, border=2)

    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer
