from django.db import models


class HorasBienestar(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    asistencia = models.ForeignKey(
        "eventos.Asistencia",
        on_delete=models.PROTECT,
        related_name="horas_bienestar"
    )

    asignado_por = models.ForeignKey(
        "usuarios.PersonalBienestar",
        on_delete=models.PROTECT,
        related_name="horas_asignadas"
    )

    # ---------- Información general ----------

    cantidad_horas = models.PositiveIntegerField()

    motivo = models.CharField(
        max_length=255
    )

    observaciones = models.CharField(
        max_length=255,
        blank=True
    )

    # ---------- Fechas ----------

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Horas de Bienestar"
        verbose_name_plural = "Horas de Bienestar"

    def __str__(self):
        return f"{self.cantidad_horas}h - {self.asistencia}"
