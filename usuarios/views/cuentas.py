"""
Cuentas de usuario: creación por un administrador, perfil del aprendiz y cambio de contraseña.
"""

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from core.services.auditoria import registrar as auditar
from usuarios.decorators import administrador_requerido
from usuarios.forms import (
    CambiarContrasenaForm,
    CrearUsuarioAdminForm,
    PerfilAprendizForm,
)
from usuarios.models import Aprendiz
from usuarios.services import crear_usuario_administrativo
from usuarios.services.perfil import actualizar_perfil_aprendiz


@administrador_requerido
def crear_usuario_admin(request):
    """
    Un Administrador crea, desde el panel, cualquier tipo de cuenta:
    Aprendiz, Personal de Bienestar o incluso otro Administrador.
    A diferencia de registro_aprendiz, aquí la persona que llena el
    formulario NO es quien va a usar la cuenta -- por eso no hace
    login() al final, solo confirma que se creó.
    """

    form = CrearUsuarioAdminForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        usuario, perfil = crear_usuario_administrativo(
            tipo_documento=form.cleaned_data["tipo_documento"],
            numero_documento=form.cleaned_data["numero_documento"],
            nombres=form.cleaned_data["nombres"],
            apellidos=form.cleaned_data["apellidos"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            tipo_perfil=form.cleaned_data["tipo_perfil"],
            grupo=form.cleaned_data.get("grupo"),
            cargo=form.cleaned_data.get("cargo"),
        )

        auditar(
            "usuario_creado",
            f"Se creó la cuenta de {usuario.get_full_name()} ({usuario.tipo_documento} "
            f"{usuario.numero_documento}) como {form.cleaned_data['tipo_perfil']}.",
            request=request,
            detalles={"tipo_perfil": form.cleaned_data["tipo_perfil"]},  # nunca la contraseña
        )
        messages.success(
            request,
            f"Cuenta creada correctamente para {usuario.get_full_name()} "
            f"({dict(form.fields['tipo_perfil'].choices)[form.cleaned_data['tipo_perfil']]})."
        )
        return redirect("usuarios:crear_usuario")

    return render(request, "usuarios/crear_usuario.html", {"form": form})


# ---------------------------------------------------------------------------
# Mi perfil (aprendiz)
# ---------------------------------------------------------------------------

@login_required(login_url="usuarios:login")
def perfil_aprendiz(request):
    """
    "Mi perfil": el aprendiz ve y actualiza sus propios datos de contacto. El
    documento, el programa, la jornada y el grupo se muestran pero solo los
    cambia el personal de Bienestar. Cada persona solo llega a SU perfil: el
    aprendiz se toma de request.user, nunca de la URL.
    """

    if not hasattr(request.user, "aprendiz"):
        return redirect("usuarios:dashboard")

    aprendiz = Aprendiz.objects.select_related(
        "usuario", "grupo__jornada", "grupo__programa_formacion__nivel_formacion"
    ).get(usuario=request.user)

    form = PerfilAprendizForm(request.POST or None, aprendiz=aprendiz)

    if request.method == "POST" and form.is_valid():
        actualizar_perfil_aprendiz(aprendiz, form.cleaned_data)
        messages.success(request, "Tus datos se actualizaron correctamente.")
        return redirect("usuarios:perfil")

    return render(request, "usuarios/perfil.html", {
        "form": form,
        "aprendiz": aprendiz,
    })


class CambiarContrasenaView(auth_views.PasswordChangeView):
    """Cambio de contraseña de cualquier usuario con sesión iniciada."""

    form_class = CambiarContrasenaForm
    template_name = "usuarios/cambiar_contrasena.html"
    success_url = reverse_lazy("usuarios:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Tu contraseña se cambió correctamente.")
        respuesta = super().form_valid(form)
        auditar("contrasena_cambiada", "La persona cambió su propia contraseña.", request=self.request)
        return respuesta
