from django.db import models

TIPO_CHOICES = [
    ("inscripcion", "Inscripción"),
    ("cancelacion", "Cancelación"),
    ("recordatorio", "Recordatorio"),
    ("horas", "Horas de bienestar"),
    ("evento", "Evento"),
    ("general", "General"),
]


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

    # Tipo: solo sirve para elegir el ícono/color en la lista.
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default="general"
    )

    # Adónde lleva la notificación al abrirla (ruta interna, ej. "/eventos/3/").
    # Vacío = no lleva a ningún lado en particular.
    url = models.CharField(
        max_length=200,
        blank=True
    )

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
        ordering = ["-fecha_creacion", "-id"]
        indexes = [
            models.Index(fields=["usuario", "leida"]),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.usuario}"
