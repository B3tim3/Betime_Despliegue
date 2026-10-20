from django.db import transaction
from django.utils import timezone

from usuarios.models import Administrador, Aprendiz, PersonalBienestar, Usuario


@transaction.atomic
def registrar_aprendiz(*, tipo_documento, numero_documento, nombres, apellidos, email, password, ficha):
    """
    Crea el Usuario y su perfil de Aprendiz de forma atómica.
    Si algo falla, no queda ningún registro a medias.
    """

    usuario = Usuario.objects.create_user(
        numero_documento=numero_documento,
        password=password,
        tipo_documento=tipo_documento,
        nombres=nombres,
        apellidos=apellidos,
        email=email,
    )

    aprendiz = Aprendiz.objects.create(
        usuario=usuario,
        ficha=ficha,
        fecha_ingreso=timezone.now().date(),
    )

    return usuario, aprendiz


@transaction.atomic
def crear_usuario_administrativo(*, tipo_documento, numero_documento, nombres, apellidos,
                                   email, password, tipo_perfil, ficha=None, cargo=None):
    """
    Crea un Usuario y su perfil correspondiente, elegido por un
    Administrador desde el panel (no por la persona misma, como sí
    pasa con el auto-registro de aprendices).

    tipo_perfil: "aprendiz", "bienestar" o "administrador" -- decide
    qué tabla de perfil se crea. Los campos que no aplican a un tipo
    de perfil (ficha para bienestar/administrador, cargo para
    aprendiz/administrador) simplemente se ignoran.
    """

    usuario = Usuario.objects.create_user(
        numero_documento=numero_documento,
        password=password,
        tipo_documento=tipo_documento,
        nombres=nombres,
        apellidos=apellidos,
        email=email,
    )

    if tipo_perfil == "aprendiz":
        perfil = Aprendiz.objects.create(
            usuario=usuario,
            ficha=ficha,
            fecha_ingreso=timezone.now().date(),
        )
    elif tipo_perfil == "bienestar":
        perfil = PersonalBienestar.objects.create(
            usuario=usuario,
            cargo=cargo,
            fecha_ingreso=timezone.now().date(),
            estado="activo",
        )
    elif tipo_perfil == "administrador":
        perfil = Administrador.objects.create(
            usuario=usuario,
            fecha_ingreso=timezone.now().date(),
        )
    else:
        raise ValueError(f"Tipo de perfil desconocido: {tipo_perfil!r}")

    return usuario, perfil
