"""
python manage.py optimizar_imagenes [--dry-run]

Pasa por la optimización (WebP, máx. 1600 px, miniatura) las imágenes que ya estaban
subidas antes de existir esta función. Es seguro repetirlo: las que ya son .webp con
miniatura se saltan. Con --dry-run solo cuenta cuánto se ahorraría.
"""

import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from bienestar.models import MiembroBienestar
from core.services import imagenes
from eventos.models import Evento
from publicaciones.models import Publicacion

OBJETIVOS = [(Evento, "imagen"), (Publicacion, "imagen"), (MiembroBienestar, "foto")]


def _mb(n):
    return f"{n / 1024 / 1024:.2f} MB"


class Command(BaseCommand):
    help = "Reduce y convierte a WebP las imágenes ya subidas (con --dry-run solo informa)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No cambia nada, solo informa.")

    def handle(self, *args, dry_run=False, **opciones):
        antes = despues = procesadas = saltadas = errores = 0

        for modelo, campo in OBJETIVOS:
            storage = modelo._meta.get_field(campo).storage
            for obj in modelo.objects.exclude(**{campo: ""}).exclude(**{f"{campo}__isnull": True}):
                archivo = getattr(obj, campo)
                nombre = archivo.name
                ya_listo = (nombre.lower().endswith(".webp") and storage.exists(imagenes.nombre_mini(nombre)))
                if ya_listo or not storage.exists(nombre):
                    saltadas += 1
                    continue
                try:
                    with storage.open(nombre, "rb") as f:
                        original = f.read()
                    tam_antes = len(original)
                    grande, mini = imagenes.optimizar(ContentFile(original))
                except Exception as error:
                    errores += 1
                    self.stderr.write(f"  ! {modelo.__name__} {obj.pk} ({nombre}): {error}")
                    continue

                antes += tam_antes
                despues += len(grande) + len(mini)
                procesadas += 1
                if dry_run:
                    continue

                carpeta = os.path.dirname(nombre)
                nuevo = storage.save(os.path.join(carpeta, imagenes.nombre_webp(nombre)), ContentFile(grande))
                storage.save(imagenes.nombre_mini(nuevo), ContentFile(mini))
                # Se actualiza sin pasar por save() (no volver a procesar) y luego se borra la vieja.
                modelo.objects.filter(pk=obj.pk).update(**{campo: nuevo})
                if nuevo != nombre:
                    storage.delete(nombre)

        self.stdout.write(self.style.SUCCESS(
            f"{'[SIMULACIÓN] ' if dry_run else ''}Procesadas: {procesadas} · ya listas o sin archivo: {saltadas} · errores: {errores}"))
        if procesadas:
            self.stdout.write(f"Antes: {_mb(antes)} -> Después: {_mb(despues)} "
                              f"(ahorro {_mb(antes - despues)}, {100 - despues * 100 // max(antes, 1)} %)")
