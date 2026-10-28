from django.db import models
from django.utils import timezone

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

    # ---------- Estado automático ----------
    # programado / en curso / finalizado salen de las fechas; "cancelado" es el
    # único que se pone a mano y nunca se pisa (ver eventos/services/estados.py).

    @staticmethod
    def calcular_estado(fecha_inicio, fecha_fin, ahora=None):
        ahora = ahora or timezone.now()
        if ahora >= fecha_fin:
            return "finalizado"
        if ahora >= fecha_inicio:
            return "en_curso"
        return "programado"

    @property
    def estado_actual(self):
        """El estado de AHORA MISMO, sin depender de que la base de datos esté al día."""
        if self.estado == "cancelado":
            return "cancelado"
        return self.calcular_estado(self.fecha_inicio, self.fecha_fin)

    def save(self, *args, **kwargs):
        if self.estado != "cancelado":
            self.estado = self.calcular_estado(self.fecha_inicio, self.fecha_fin)
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = list(kwargs["update_fields"]) + ["estado"]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo
