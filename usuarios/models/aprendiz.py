from django.db import models

ESTADO_CHOICES = [
    ("activo", "Activo"),
    ("retirado", "Retirado"),
    ("egresado", "Egresado"),
]


class Aprendiz(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    usuario = models.OneToOneField(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="aprendiz"
    )

    ficha = models.ForeignKey(
        "usuarios.Ficha",
        on_delete=models.PROTECT,
        related_name="aprendices"
    )

    # ---------- Información general ----------

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
        verbose_name = "Aprendiz"
        verbose_name_plural = "Aprendices"

    def __str__(self):
        return str(self.usuario)
