from django.db import models

ESTADO_CHOICES = [
    ("programado", "Programado"),
    ("en_curso", "En curso"),
    ("finalizado", "Finalizado"),
    ("cancelado", "Cancelado"),
]


class Evento(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Información general ----------

    titulo = models.CharField(
        max_length=150
    )

    descripcion = models.TextField(
        blank=True
    )

    lugar = models.CharField(
        max_length=150
    )

    horas_otorgadas = models.PositiveIntegerField(
        default=0
    )

    imagen = models.ImageField(
        upload_to="eventos/",
        null=True,
        blank=True
    )

    # ---------- Relaciones ----------

    creado_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="eventos_creados"
    )

    # ---------- Fechas ----------

    fecha_inicio = models.DateTimeField()

    fecha_fin = models.DateTimeField()

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="programado"
    )

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self):
        return self.titulo
