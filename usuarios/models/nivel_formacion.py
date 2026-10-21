from django.db import models


class NivelFormacion(models.Model):
    """
    Catálogo de niveles de formación (Técnico, Tecnólogo, ...). Lo
    administra el Administrador desde el panel: puede agregar, editar y
    quitar niveles sin tocar el código. Cada ProgramaFormacion apunta a
    uno de estos niveles.
    """

    id = models.BigAutoField(primary_key=True)

    nombre = models.CharField(
        max_length=60,
        unique=True
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Nivel de formación"
        verbose_name_plural = "Niveles de formación"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
