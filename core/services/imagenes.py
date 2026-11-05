"""
Imágenes: reducir, comprimir y crear miniaturas.

Por qué existe: una foto de celular pesa 3-8 MB y lo que se muestra en pantalla
necesita ~200 KB. Sin esto, 120 imágenes al año ocuparían cientos de MB (el disco es
lo primero que se llena, mucho antes que la base de datos).

Reglas:
  * Máximo 5 MB por imagen subida (se rechaza con un mensaje claro).
  * Se corrige la rotación (EXIF) de las fotos de celular antes de reducirlas.
  * Se guarda como WebP (calidad 80), con un máximo de 1600 px por lado.
  * Junto a cada imagen se guarda una miniatura "<nombre>_mini.webp" de 480 px.
    No hay columna en la base de datos: la miniatura se deduce del nombre.
"""

import os
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_LADO = 1600
MAX_LADO_MINI = 480
CALIDAD = 80
CALIDAD_MINI = 74


def validar_peso(archivo):
    """Rechaza imágenes de más de 5 MB. Solo mira archivos RECIÉN subidos."""
    tam = getattr(archivo, "size", None)
    if tam is not None and tam > MAX_BYTES:
        raise ValidationError(
            f"La imagen pesa {tam / 1024 / 1024:.1f} MB y el máximo permitido es "
            f"{MAX_BYTES // 1024 // 1024} MB. Redúcela o elige otra."
        )


def nombre_mini(nombre):
    """'actividades/foto.webp' -> 'actividades/foto_mini.webp'."""
    raiz, _ = os.path.splitext(nombre)
    return f"{raiz}_mini.webp"


def _abrir(archivo):
    try:
        archivo.seek(0)
    except Exception:
        pass
    try:
        imagen = Image.open(archivo)
        imagen.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValidationError("El archivo no es una imagen válida.") from error
    # Fotos de celular: el giro viene en metadatos; se aplica de verdad.
    imagen = ImageOps.exif_transpose(imagen)
    if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
        return imagen.convert("RGBA")
    return imagen.convert("RGB")


def _a_webp(imagen, max_lado, calidad):
    copia = imagen.copy()
    copia.thumbnail((max_lado, max_lado), Image.LANCZOS)
    buffer = BytesIO()
    copia.save(buffer, format="WEBP", quality=calidad, method=4)
    return buffer.getvalue()


def optimizar(archivo):
    """
    Devuelve (bytes_grande, bytes_mini) en WebP a partir de un archivo subido.
    Lanza ValidationError si no es una imagen. Un GIF animado queda con su primer cuadro.
    """
    imagen = _abrir(archivo)
    return _a_webp(imagen, MAX_LADO, CALIDAD), _a_webp(imagen, MAX_LADO_MINI, CALIDAD_MINI)


def contenido_optimizado(archivo):
    """(ContentFile grande, ContentFile mini) listos para guardar en el storage."""
    grande, mini = optimizar(archivo)
    return ContentFile(grande), ContentFile(mini)


def nombre_webp(nombre_original):
    """'Mi Foto.JPG' -> 'Mi Foto.webp' (solo el nombre, sin carpeta)."""
    raiz, _ = os.path.splitext(os.path.basename(nombre_original))
    return f"{raiz}.webp"


def borrar_con_mini(storage, nombre):
    """Borra una imagen y su miniatura. No falla si ya no existen."""
    if not nombre:
        return
    for n in (nombre, nombre_mini(nombre)):
        try:
            storage.delete(n)
        except Exception:
            pass
