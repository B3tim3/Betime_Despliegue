from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def personal_bienestar_requerido(vista):
    """
    Permite el acceso solo a usuarios con perfil de PersonalBienestar
    o Administrador. Los aprendices (o cualquier otro usuario) son
    redirigidos a su propio dashboard.
    """

    @login_required(login_url="usuarios:login")
    @wraps(vista)
    def envoltura(request, *args, **kwargs):

        usuario = request.user

        if hasattr(usuario, "personal_bienestar") or hasattr(usuario, "administrador"):
            return vista(request, *args, **kwargs)

        messages.error(request, "No tienes permisos para acceder a esa sección.")
        return redirect("usuarios:dashboard")

    return envoltura


def administrador_requerido(vista):
    """
    Permite el acceso solo a usuarios con perfil de Administrador.
    """

    @login_required(login_url="usuarios:login")
    @wraps(vista)
    def envoltura(request, *args, **kwargs):

        if hasattr(request.user, "administrador"):
            return vista(request, *args, **kwargs)

        messages.error(request, "Solo un administrador puede acceder a esta sección.")
        return redirect("usuarios:dashboard")

    return envoltura
