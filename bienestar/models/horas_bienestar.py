from django.db import models


class HorasBienestar(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    asistencia = models.ForeignKey(
        "eventos.Asistencia",
        on_delete=models.PROTECT,
        related_name="horas_bienestar",
        null=True,
        blank=True,
    )

    # Horas de bienestar por mérito (fuera de eventos): cada registro viene de UNA
    # de las dos fuentes, nunca de las dos ni de ninguna (ver Meta.constraints).
    participacion = models.OneToOneField(
        "bienestar.ParticipacionExtracurricular",
        on_delete=models.PROTECT,
        related_name="horas",
        null=True,
        blank=True,
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
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(asistencia__isnull=False, participacion__isnull=True)
                    | models.Q(asistencia__isnull=True, participacion__isnull=False)
                ),
                name="horas_una_sola_fuente",
            ),
        ]

    @property
    def concepto(self):
        """Nombre de lo que dio las horas: el evento o la actividad por mérito."""
        if self.participacion_id:
            return f"{self.participacion.actividad.titulo} (por mérito)"
        return self.asistencia.inscripcion.evento.titulo

    def __str__(self):
        return f"{self.cantidad_horas}h - {self.asistencia or self.participacion}"
