from django.db import models


class MiembroBienestar(models.Model):

    CATEGORIA_CHOICES = [
        ("salud", "Salud"),
        ("psicosocial", "Equipo Psicosocial"),
        ("deporte", "Deporte"),
        ("cultura", "Arte y Cultura"),
    ]

    id = models.BigAutoField(primary_key=True)

    # ---------- Información general ----------

    nombre = models.CharField(
        max_length=150
    )

    cargo = models.CharField(
        max_length=100
    )

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default="salud"
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
