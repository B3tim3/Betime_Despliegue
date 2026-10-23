from django.db import models


class RegistroAuditoria(models.Model):
    """
    Bitácora de acciones sensibles: quién hizo qué y cuándo.

    Sirve para responder reclamos ("¿quién me quitó las horas?", "¿quién
    cambió mi grupo?") y para detectar usos indebidos. Es de solo adición:
    un registro no se edita ni se borra desde la aplicación (ni desde el
    admin), porque una bitácora que se puede modificar no prueba nada.
    """

    ACCIONES = [
        ("aprendiz_editado", "Aprendiz editado (grupo o estado)"),
        ("aprendiz_eliminado", "Aprendiz eliminado"),
        ("asistencia", "Asistencia / horas registradas"),
        ("meta_horas", "Meta de horas cambiada"),
        ("usuario_creado", "Cuenta creada por un administrador"),
        ("evento_cancelado", "Evento cancelado"),
        ("evento_eliminado", "Evento eliminado"),
        ("catalogo_eliminado", "Registro de catálogo eliminado"),
        ("contrasena_cambiada", "Contraseña cambiada"),
        ("login_bloqueado", "Acceso bloqueado por intentos fallidos"),
    ]

    id = models.BigAutoField(primary_key=True)

    # Si la cuenta se elimina después, el registro se conserva (SET_NULL)
    # y "usuario_texto" guarda quién era.
    usuario = models.ForeignKey(
        "usuarios.Usuario", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    usuario_texto = models.CharField(max_length=200, blank=True)

    accion = models.CharField(max_length=30, choices=ACCIONES)
    descripcion = models.TextField()
    detalles = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-fecha", "-id"]
        indexes = [models.Index(fields=["accion", "fecha"])]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("Los registros de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} · {self.get_accion_display()}"
