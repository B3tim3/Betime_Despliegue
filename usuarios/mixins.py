from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class AdministradorRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Solo un Administrador puede acceder (catálogos: programas, jornadas)."""

    login_url = "usuarios:login"

    def test_func(self):
        return hasattr(self.request.user, "administrador")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Solo un administrador puede acceder a esta sección.")
            return redirect("usuarios:dashboard")
        return super().handle_no_permission()


class PersonalBienestarRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Personal de Bienestar o Administrador (fichas, aprendices)."""

    login_url = "usuarios:login"

    def test_func(self):
        usuario = self.request.user
        return hasattr(usuario, "personal_bienestar") or hasattr(usuario, "administrador")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "No tienes permisos para acceder a esa sección.")
            return redirect("usuarios:dashboard")
        return super().handle_no_permission()
