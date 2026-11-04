from django.db import models

from core.imagenes_mixin import ImagenOptimizadaMixin


class MiembroBienestar(ImagenOptimizadaMixin, models.Model):

    CAMPOS_IMAGEN = ("foto",)

    id = models.BigAutoField(primary_key=True)

    # ---------- Información general ----------

    nombre = models.CharField(
        max_length=150
    )

    cargo = models.CharField(
        max_length=100
    )

    descripcion = models.TextField(
        blank=True
    )

    foto = models.ImageField(
        upload_to="bienestar/equipo/",
        null=True,
        blank=True
    )

    correo_asesorias = models.EmailField(
        blank=True
    )

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        default="activo"
    )

    # ---------- Fechas ----------

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Miembro de Bienestar"
        verbose_name_plural = "Miembros de Bienestar"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
