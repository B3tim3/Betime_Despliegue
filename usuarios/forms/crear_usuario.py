from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from usuarios.choices import TIPO_DOCUMENTO_CHOICES
from usuarios.models import Ficha, ProgramaFormacion

TIPO_PERFIL_CHOICES = [
    ("aprendiz", "Aprendiz"),
    ("bienestar", "Personal de Bienestar"),
    ("administrador", "Administrador"),
]


class CrearUsuarioAdminForm(forms.Form):
    """
    Formulario con el que un Administrador crea, desde el panel,
    cualquier tipo de cuenta -- Aprendiz, Personal de Bienestar o
    incluso otro Administrador. Es distinto de RegistroAprendizForm
    (que usa la propia persona para auto-registrarse): aquí quien
    llena el formulario decide qué tipo de perfil crear.
    """

    tipo_perfil = forms.ChoiceField(
        choices=TIPO_PERFIL_CHOICES,
        label="Tipo de cuenta a crear",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_tipo_perfil"})
    )

    tipo_documento = forms.ChoiceField(
        choices=TIPO_DOCUMENTO_CHOICES,
        label="Tipo de documento",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    numero_documento = forms.CharField(
        label="Número de documento",
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "inputmode": "numeric",
        })
    )

    nombres = forms.CharField(
        label="Nombres",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    apellidos = forms.CharField(
        label="Apellidos",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    # ---- Solo aplica si tipo_perfil == "aprendiz" ----
    programa_formacion = forms.ModelChoiceField(
        queryset=ProgramaFormacion.objects.filter(estado="activo").order_by("nombre"),
        label="Programa de formación",
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_programa_formacion",
        }),
        empty_label="Selecciona el programa"
    )

    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.none(),
        label="Ficha",
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_ficha",
        }),
        empty_label="Selecciona primero el programa"
    )

    # ---- Solo aplica si tipo_perfil == "bienestar" ----
    cargo = forms.CharField(
        label="Cargo",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ej. Coordinador de Bienestar",
        })
    )

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        })
    )

    password_confirm = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "new-password",
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Mismo truco que en RegistroAprendizForm: si el formulario se
        # reenvía tras un error de validación con un programa ya
        # elegido, se llena el <select> de fichas con las de ese
        # programa para que el valor enviado siga siendo válido.
        programa_id = self.data.get("programa_formacion") if self.data else None

        if programa_id:
            self.fields["ficha"].queryset = Ficha.objects.filter(
                programa_formacion_id=programa_id
            ).order_by("numero_ficha")

    def clean_numero_documento(self):
        numero_documento = self.cleaned_data["numero_documento"]

        Usuario = get_user_model()
        if Usuario.objects.filter(numero_documento=numero_documento).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este número de documento."
            )

        return numero_documento

    def clean_email(self):
        email = self.cleaned_data["email"]

        Usuario = get_user_model()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo electrónico."
            )

        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")

        tipo_perfil = cleaned_data.get("tipo_perfil")

        if tipo_perfil == "aprendiz" and not cleaned_data.get("ficha"):
            self.add_error("ficha", "Selecciona una ficha para el aprendiz.")

        if tipo_perfil == "bienestar" and not cleaned_data.get("cargo"):
            self.add_error("cargo", "Indica el cargo de esta persona en Bienestar.")

        return cleaned_data
