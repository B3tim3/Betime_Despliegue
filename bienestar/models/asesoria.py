from django.db import models

ESTADO_CHOICES = [
    ("solicitada", "Solicitada"),
    ("confirmada", "Confirmada"),
    ("realizada", "Realizada"),
    ("cancelada", "Cancelada"),
]


class Asesoria(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    aprendiz = models.ForeignKey(
        "usuarios.Aprendiz",
        on_delete=models.CASCADE,
        related_name="asesorias"
    )

    personal_bienestar = models.ForeignKey(
        "usuarios.PersonalBienestar",
        on_delete=models.PROTECT,
        related_name="asesorias_atendidas",
        null=True,
        blank=True
    )

    # ---------- Información general ----------

    tipo = models.CharField(
        max_length=50
    )

    descripcion = models.TextField(
        blank=True
    )

    observaciones = models.TextField(
        blank=True
    )

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="solicitada"
    )

    # ---------- Fechas ----------

    fecha_solicitud = models.DateTimeField(
        auto_now_add=True
    )

    fecha_atencion = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Asesoría"
        verbose_name_plural = "Asesorías"

    def __str__(self):
        return f"{self.tipo} - {self.aprendiz}"
