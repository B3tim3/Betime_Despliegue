from django.db import models


class Administrador(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    usuario = models.OneToOneField(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="administrador"
    )

    # ---------- Fechas ----------

    fecha_ingreso = models.DateField()

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"

    def __str__(self):
        return str(self.usuario)
