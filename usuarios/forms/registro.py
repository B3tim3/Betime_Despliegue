from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from usuarios.choices import TIPO_DOCUMENTO_CHOICES
from usuarios.models import Ficha, ProgramaFormacion


class RegistroAprendizForm(forms.Form):

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
            "autocomplete": "username",
            "inputmode": "numeric",
        })
    )

    nombres = forms.CharField(
        label="Nombres",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "autocomplete": "given-name",
        })
    )

    apellidos = forms.CharField(
        label="Apellidos",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "autocomplete": "family-name",
        })
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
        })
    )

    programa_formacion = forms.ModelChoiceField(
        queryset=ProgramaFormacion.objects.filter(estado="activo").order_by("nombre"),
        label="Programa de formación",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_programa_formacion",
        }),
        empty_label="Selecciona tu programa de formación"
    )

    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.none(),
        label="Ficha",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_ficha",
        }),
        empty_label="Selecciona primero tu programa de formación"
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

        # El <select> de fichas empieza vacío. Si el formulario viene con un
        # programa de formación ya elegido (al reenviar el POST, por ejemplo
        # tras un error de validación), lo llenamos con las fichas de ese
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

        return cleaned_data
