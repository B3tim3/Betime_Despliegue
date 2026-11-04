import secrets

from django.db import models
from django.utils import timezone

# Sin 0/O, 1/I/L: el código se dicta en voz alta o se escribe en un tablero.
ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generar_codigo():
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(6))


class ActividadExtracurricular(models.Model):
    """
    Una forma de dar horas de bienestar FUERA de los eventos: por portar
    bien el uniforme, por atender una charla en el aula, etc.

    No aparece en la sección pública de Eventos. Cada actividad tiene un
    código corto que Bienestar comparte; los aprendices lo ingresan en
    "Recibir horas de bienestar por mérito" y quedan en la lista de la actividad
    (modo código). También se puede escanear el QR personal del aprendiz
    (modo QR). Las dos formas conviven en la misma actividad.
    """

    ESTADOS = [("abierta", "Abierta"), ("cerrada", "Cerrada")]

    id = models.BigAutoField(primary_key=True)
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    horas = models.PositiveIntegerField(default=1, help_text="Horas por defecto para cada aprendiz.")
    fecha = models.DateField(default=timezone.localdate)
    codigo = models.CharField(max_length=8, unique=True, editable=False)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="abierta")
    creado_por = models.ForeignKey(
        "usuarios.PersonalBienestar", on_delete=models.PROTECT,
        related_name="actividades_extracurriculares",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Actividad por mérito"
        verbose_name_plural = "Actividades por mérito"
        ordering = ["-fecha", "-id"]

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.nuevo_codigo_unico()
        super().save(*args, **kwargs)

    @classmethod
    def nuevo_codigo_unico(cls):
        while True:
            codigo = generar_codigo()
            if not cls.objects.filter(codigo=codigo).exists():
                return codigo

    @property
    def abierta(self):
        return self.estado == "abierta"

    def __str__(self):
        return f"{self.titulo} ({self.codigo})"


class ParticipacionExtracurricular(models.Model):
    """Un aprendiz dentro de una actividad: pendiente de horas u otorgada."""

    ESTADOS = [("pendiente", "Pendiente"), ("otorgada", "Horas otorgadas")]
    METODOS = [("codigo", "Código"), ("qr", "QR"), ("manual", "Manual")]

    id = models.BigAutoField(primary_key=True)
    actividad = models.ForeignKey(
        ActividadExtracurricular, on_delete=models.CASCADE, related_name="participaciones",
    )
    aprendiz = models.ForeignKey(
        "usuarios.Aprendiz", on_delete=models.CASCADE, related_name="participaciones_extracurriculares",
    )
    estado = models.CharField(max_length=10, choices=ESTADOS, default="pendiente")
    metodo = models.CharField(max_length=10, choices=METODOS, default="codigo")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Participación por mérito"
        verbose_name_plural = "Participaciones por mérito"
        unique_together = [("actividad", "aprendiz")]
        ordering = ["aprendiz__usuario__apellidos", "aprendiz__usuario__nombres"]

    def __str__(self):
        return f"{self.aprendiz} en {self.actividad.titulo}"
