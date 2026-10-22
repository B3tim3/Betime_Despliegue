import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm

from usuarios.choices import GENERO_CHOICES


class PerfilAprendizForm(forms.Form):
    """
    Edición de los datos del propio aprendiz ("Mi perfil").

    Se puede cambiar: nombres, apellidos, género, correo y teléfono.

    NO se puede cambiar el tipo ni el número de documento (son la
    identidad con la que inicia sesión) NI el programa, la jornada o el
    grupo: esos datos alimentan los listados oficiales de asistencia y
    cambiarlos por cuenta propia se presta a errores o fraudes. Solo el
    personal de Bienestar o un administrador los modifica
    (Panel -> Aprendices -> Editar).

    Recibe el aprendiz con `aprendiz=...`.
    """

    nombres = forms.CharField(
        label="Nombres", max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
    )
    apellidos = forms.CharField(
        label="Apellidos", max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
    )
    genero = forms.ChoiceField(
        choices=[("", "Selecciona")] + list(GENERO_CHOICES),
        label="Género",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    telefono = forms.CharField(
        label="Teléfono de contacto", max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control", "autocomplete": "tel", "inputmode": "tel",
            "placeholder": "Ej. 3001234567",
        }),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )

    def __init__(self, *args, aprendiz, **kwargs):
        self.aprendiz = aprendiz
        self.usuario = aprendiz.usuario

        if not args or args[0] is None:
            kwargs.setdefault("initial", {
                "nombres": self.usuario.nombres,
                "apellidos": self.usuario.apellidos,
                "genero": self.usuario.genero,
                "telefono": self.usuario.telefono,
                "email": self.usuario.email,
            })

        super().__init__(*args, **kwargs)

    # ---------- Validaciones ----------

    def clean_nombres(self):
        return " ".join(self.cleaned_data["nombres"].split())

    def clean_apellidos(self):
        return " ".join(self.cleaned_data["apellidos"].split())

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        Usuario = get_user_model()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.usuario.pk).exists():
            raise forms.ValidationError(
                "Ya existe otra cuenta registrada con este correo electrónico."
            )
        return email

    def clean_telefono(self):
        telefono = re.sub(r"[\s\-().]", "", self.cleaned_data["telefono"])
        if not re.fullmatch(r"\+?\d{7,13}", telefono):
            raise forms.ValidationError(
                "Ingresa un número de teléfono válido (solo números, entre 7 y 13 dígitos)."
            )
        return telefono


class CambiarContrasenaForm(PasswordChangeForm):
    """El formulario estándar de Django con las clases de Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        autocompletar = {
            "old_password": "current-password",
            "new_password1": "new-password",
            "new_password2": "new-password",
        }
        for nombre, campo in self.fields.items():
            campo.widget.attrs.update({
                "class": "form-control",
                "autocomplete": autocompletar[nombre],
            })
