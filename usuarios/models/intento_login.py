from django.db import models


class IntentoFallido(models.Model):
    """
    Un intento de inicio de sesión que falló. Sirve para bloquear
    temporalmente un documento cuando alguien prueba contraseñas
    (ver usuarios/services/bloqueo.py).

    Se guarda el documento TAL COMO se escribió en el formulario, exista
    o no en el sistema: así el bloqueo se comporta igual para documentos
    reales y falsos y no revela cuáles están registrados.
    """

    id = models.BigAutoField(primary_key=True)

    numero_documento = models.CharField(max_length=20)

    # Informativa (para revisar en el admin); el bloqueo es por documento.
    ip = models.GenericIPAddressField(null=True, blank=True)

    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Intento fallido de acceso"
        verbose_name_plural = "Intentos fallidos de acceso"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["numero_documento", "fecha"]),
        ]

    def __str__(self):
        return f"{self.numero_documento} - {self.fecha:%d/%m/%Y %H:%M}"
