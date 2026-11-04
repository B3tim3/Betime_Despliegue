"""
python manage.py limpiar_archivos_huerfanos [--borrar]

Busca en la carpeta de imágenes (eventos/, publicaciones/, bienestar/equipo/) archivos
que NINGÚN registro usa (por ejemplo, fotos viejas de antes de que se borraran solas).
Por defecto solo los LISTA; con --borrar los elimina. Las miniaturas se consideran
usadas si su imagen grande lo está.
"""

from django.core.management.base import BaseCommand

from bienestar.models import MiembroBienestar
from core.services import imagenes
from eventos.models import Evento
from publicaciones.models import Publicacion

OBJETIVOS = [(Evento, "imagen"), (Publicacion, "imagen"), (MiembroBienestar, "foto")]


def _archivos(storage, carpeta):
    """Todos los archivos bajo una carpeta, recursivo."""
    try:
        dirs, files = storage.listdir(carpeta)
    except (FileNotFoundError, NotADirectoryError):
        return
    for f in files:
        yield f"{carpeta}/{f}"
    for d in dirs:
        yield from _archivos(storage, f"{carpeta}/{d}")


class Command(BaseCommand):
    help = "Lista (o borra con --borrar) archivos de imagen que ningún registro usa."

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Elimina los archivos huérfanos.")

    def handle(self, *args, borrar=False, **opciones):
        total = peso = 0
        for modelo, campo in OBJETIVOS:
            storage = modelo._meta.get_field(campo).storage
            carpeta = modelo._meta.get_field(campo).upload_to.rstrip("/")
            usados = set()
            for nombre in modelo.objects.exclude(**{campo: ""}).exclude(**{f"{campo}__isnull": True}).values_list(campo, flat=True):
                usados.add(nombre)
                usados.add(imagenes.nombre_mini(nombre))
            for nombre in _archivos(storage, carpeta):
                if nombre in usados:
                    continue
                tam = storage.size(nombre)
                total += 1
                peso += tam
                self.stdout.write(f"  {'borrado' if borrar else 'huérfano'}: {nombre} ({tam / 1024:.0f} KB)")
                if borrar:
                    storage.delete(nombre)
        accion = "Borrados" if borrar else "Encontrados"
        self.stdout.write(self.style.SUCCESS(f"{accion}: {total} archivo(s), {peso / 1024 / 1024:.2f} MB."))
        if total and not borrar:
            self.stdout.write("Para eliminarlos: python manage.py limpiar_archivos_huerfanos --borrar")
