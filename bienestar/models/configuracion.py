from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ConfiguracionBienestar(models.Model):
    """
    Ajustes generales de Bienestar que el administrador puede cambiar sin
    tocar el código. Hoy solo guarda la meta de horas de bienestar que cada
    aprendiz debe completar (40 por defecto).

    Es un registro ÚNICO (siempre pk=1): se obtiene con
    ConfiguracionBienestar.obtener(), que lo crea con los valores por defecto
    la primera vez. Así no hace falta ninguna migración de datos y nunca
    puede haber dos configuraciones distintas.
    """

    META_HORAS_POR_DEFECTO = 40

    meta_horas = models.PositiveIntegerField(
        "Meta de horas de bienestar",
        default=META_HORAS_POR_DEFECTO,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Horas de bienestar que cada aprendiz debe completar. "
                  "Se usa en la barra de progreso del panel del aprendiz.",
    )

    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Bienestar"
        verbose_name_plural = "Configuración de Bienestar"

    def save(self, *args, **kwargs):
        self.pk = 1   # registro único
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        configuracion, _ = cls.objects.get_or_create(pk=1)
        return configuracion

    def __str__(self):
        return f"Configuración de Bienestar (meta: {self.meta_horas} h)"
