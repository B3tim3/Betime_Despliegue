from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from usuarios.choices import TIPO_DOCUMENTO_CHOICES
from usuarios.managers import UsuarioManager


class Usuario(AbstractBaseUser, PermissionsMixin):

    id = models.BigAutoField(primary_key=True)

    # ---------- Información de autenticación ----------

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPO_DOCUMENTO_CHOICES
    )

    numero_documento = models.CharField(
        max_length=20,
        unique=True
    )

    nombres = models.CharField(
        max_length=100
    )

    apellidos = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True
    )

    # ---------- Estados ----------

    is_active = models.BooleanField(
        default=True
    )

    is_staff = models.BooleanField(
        default=False
    )

    # ---------- Fechas ----------

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    # ---------- Manager ----------

    objects = UsuarioManager()

    # ---------- Login ----------

    USERNAME_FIELD = "numero_documento"

    REQUIRED_FIELDS = ["tipo_documento", "nombres", "apellidos"]

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name()} ({self.numero_documento})"

    def get_full_name(self):
        return f"{self.nombres} {self.apellidos}".strip()

    def get_short_name(self):
        return self.nombres
