import uuid

from django.db import models
from django.utils import timezone

ESTADO_CHOICES = [
    ("inscrito", "Inscrito"),
    ("asistio", "Asistió"),
    ("no_asistio", "No asistió"),
    ("cancelada", "Cancelada"),
]


class Inscripcion(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    evento = models.ForeignKey(
        "eventos.Evento",
        on_delete=models.CASCADE,
        related_name="inscripciones"
    )

    aprendiz = models.ForeignKey(
        "usuarios.Aprendiz",
        on_delete=models.CASCADE,
        related_name="inscripciones"
    )

    # ---------- QR ----------
    # Token único e imposible de adivinar -- es lo que se codifica en
    # el QR de esta inscripción en particular. Un UUID en vez del "id"
    # normal, porque el id es un número secuencial fácil de adivinar
    # (1, 2, 3...) y cualquiera podría probar números al azar.

    token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="inscrito"
    )

    # ---------- Recordatorio ----------
    # True cuando ya se le avisó (campanita + correo) que el evento está
    # cerca. Evita avisar dos veces; se reinicia si el evento cambia de
    # fecha o si la persona cancela y se vuelve a inscribir.

    recordatorio_enviado = models.BooleanField(
        default=False
    )

    # ---------- Fechas ----------

    fecha_inscripcion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"
        unique_together = ("evento", "aprendiz")

    @property
    def puede_cancelarse(self):
        """
        El aprendiz solo puede cancelar mientras la inscripción siga
        activa y el evento esté programado y no haya empezado. Después,
        la asistencia ya la maneja Bienestar. (Usar select_related("evento")
        en los listados para no hacer una consulta por fila.)
        """
        return (
            self.estado == "inscrito"
            and self.evento.estado_actual == "programado"
            and self.evento.fecha_inicio > timezone.now()
        )

    def __str__(self):
        return f"{self.aprendiz} - {self.evento}"
