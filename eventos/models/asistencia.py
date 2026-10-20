from django.db import models


class Asistencia(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    inscripcion = models.OneToOneField(
        "eventos.Inscripcion",
        on_delete=models.CASCADE,
        related_name="asistencia"
    )

    # ---------- Información general ----------

    asistio = models.BooleanField(
        default=False
    )

    observaciones = models.CharField(
        max_length=255,
        blank=True
    )

    # ---------- Fechas ----------

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"

    def __str__(self):
        return f"Asistencia - {self.inscripcion}"
