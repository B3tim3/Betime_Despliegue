from django.db import models

ESTADO_CHOICES = [
    ("activo", "Activo"),
    ("inactivo", "Inactivo"),
]


class ProgramaFormacion(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Información general ----------

    nombre = models.CharField(
        max_length=150
    )

    codigo = models.CharField(
        max_length=20,
        unique=True
    )

    nivel_formacion = models.CharField(
        max_length=50
    )

    duracion_meses = models.PositiveIntegerField()

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
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
        verbose_name = "Programa de Formación"
        verbose_name_plural = "Programas de Formación"

    def __str__(self):
        return self.nombre
