from django.db import models


class Jornada(models.Model):

    id = models.BigAutoField(primary_key=True)

    nombre = models.CharField(
        max_length=30,
        unique=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Jornada"
        verbose_name_plural = "Jornadas"

    def __str__(self):
        return self.nombre
