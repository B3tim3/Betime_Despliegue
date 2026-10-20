from django.db import models


class Notificacion(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="notificaciones"
    )

    # ---------- Información general ----------

    titulo = models.CharField(
        max_length=150
    )

    mensaje = models.TextField()

    leida = models.BooleanField(
        default=False
    )

    # ---------- Fechas ----------

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.titulo} - {self.usuario}"
