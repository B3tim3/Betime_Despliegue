from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone


class UsuarioManager(BaseUserManager):

    def create_user(self, numero_documento, password=None, **extra_fields):

        if not numero_documento:
            raise ValueError("El número de documento es obligatorio.")

        usuario = self.model(
            numero_documento=numero_documento,
            **extra_fields
        )

        usuario.set_password(password)

        usuario.save(using=self._db)

        return usuario

    def create_superuser(self, numero_documento, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        usuario = self.create_user(
            numero_documento,
            password,
            **extra_fields
        )

        # Un superusuario también debe poder usar el panel de la app
        # (no solo /admin/). Sin esto, createsuperuser deja la cuenta
        # sin ningún perfil (Administrador/PersonalBienestar/Aprendiz),
        # y dashboard_redirect lo rebota de vuelta al login porque no
        # encuentra a qué panel mandarlo.
        #
        # El import va aquí adentro (no arriba del archivo) para evitar
        # una importación circular: usuario.py importa este manager,
        # así que este manager no puede importar de usuarios.models al
        # nivel del módulo.
        from usuarios.models import Administrador

        Administrador.objects.get_or_create(
            usuario=usuario,
            defaults={"fecha_ingreso": timezone.now().date()},
        )

        return usuario
