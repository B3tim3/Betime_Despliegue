from django.db import models

ESTADO_CHOICES = [
    ("activa", "Activo"),
    ("cerrada", "Cerrado"),
]


class Grupo(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    programa_formacion = models.ForeignKey(
        "usuarios.ProgramaFormacion",
        on_delete=models.PROTECT,
        related_name="grupos"
    )

    # ---------- Información general ----------

    numero_grupo = models.CharField(
        "número de grupo",
        max_length=20,
        unique=True
    )

    jornada = models.ForeignKey(
        "usuarios.Jornada",
        on_delete=models.PROTECT,
        related_name="grupos"
    )

    # ---------- Fechas ----------

    fecha_inicio = models.DateField()

    fecha_fin = models.DateField()

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="activa"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"

    def __str__(self):
        return self.numero_grupo
