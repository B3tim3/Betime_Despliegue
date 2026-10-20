from django.db import models

ESTADO_CHOICES = [
    ("activo", "Activo"),
    ("inactivo", "Inactivo"),
]


class PersonalBienestar(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    usuario = models.OneToOneField(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="personal_bienestar"
    )

    # ---------- Información general ----------

    cargo = models.CharField(
        max_length=100
    )

    fecha_ingreso = models.DateField()

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="activo"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Personal de Bienestar"
        verbose_name_plural = "Personal de Bienestar"

    def __str__(self):
        return str(self.usuario)
