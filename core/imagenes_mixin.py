"""
Mixin para modelos con imágenes (Evento, Publicacion, MiembroBienestar).

Al guardar:
  * Si se subió una imagen NUEVA -> se reduce/convierte a WebP y se crea su miniatura.
  * Si la imagen cambió o se quitó -> el archivo VIEJO (y su miniatura) se borra.
Al eliminar el registro -> también se borran sus archivos.

Los borrados se hacen con transaction.on_commit: solo ocurren si la base de datos
confirma el cambio, así un error a medias nunca deja un registro sin su imagen.

Sin campos nuevos: no genera migraciones.
"""

import logging

from django.db import models, transaction
from django.db.models.signals import post_delete

from core.services import imagenes

log = logging.getLogger(__name__)


class ImagenOptimizadaMixin(models.Model):

    # Nombres de los campos ImageField del modelo que se procesan.
    CAMPOS_IMAGEN = ("imagen",)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        a_borrar = []
        actualizados = kwargs.get("update_fields")
        for campo in self.CAMPOS_IMAGEN:
            # save(update_fields=[...]) (p. ej. el cambio automático de estado) no toca imágenes.
            if actualizados is not None and campo not in actualizados:
                continue
            a_borrar += self._procesar_campo(campo)
        super().save(*args, **kwargs)
        if a_borrar:
            almacenamiento = {c: self._meta.get_field(c).storage for c in self.CAMPOS_IMAGEN}
            for campo, nombre in a_borrar:
                transaction.on_commit(lambda s=almacenamiento[campo], n=nombre: imagenes.borrar_con_mini(s, n))

    def _procesar_campo(self, campo):
        """Optimiza la imagen nueva y devuelve [(campo, nombre_viejo)] a borrar tras guardar."""
        archivo = getattr(self, campo)
        nueva_subida = bool(archivo) and not getattr(archivo, "_committed", True)
        quitada = not archivo

        # Solo si la imagen cambió (nueva o quitada) hace falta saber cuál había antes.
        viejo = None
        if self.pk and (nueva_subida or quitada):
            viejo = type(self).objects.filter(pk=self.pk).values_list(campo, flat=True).first()

        a_borrar = []

        if nueva_subida:
            try:
                grande, mini = imagenes.contenido_optimizado(archivo.file)
                nombre = imagenes.nombre_webp(archivo.name)
                archivo.save(nombre, grande, save=False)          # aplica upload_to y evita choques de nombre
                self._meta.get_field(campo).storage.save(imagenes.nombre_mini(archivo.name), mini)
            except Exception:
                # Mejor guardar la original que perder la subida: queda registrado el motivo.
                log.warning("No se pudo optimizar la imagen de %s %s", type(self).__name__, self.pk, exc_info=True)

        if viejo and viejo != (archivo.name if archivo else ""):
            a_borrar.append((campo, viejo))
        return a_borrar


def _borrar_archivos_al_eliminar(sender, instance, **kwargs):
    if not isinstance(instance, ImagenOptimizadaMixin):
        return
    for campo in instance.CAMPOS_IMAGEN:
        archivo = getattr(instance, campo)
        if archivo and archivo.name:
            almacenamiento = instance._meta.get_field(campo).storage
            transaction.on_commit(lambda s=almacenamiento, n=archivo.name: imagenes.borrar_con_mini(s, n))


post_delete.connect(_borrar_archivos_al_eliminar, dispatch_uid="betime.borrar_imagenes")
