from django import forms
from django.contrib.auth import get_user_model

from usuarios.choices import TIPO_DOCUMENTO_CHOICES


class LoginForm(forms.Form):

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

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "autocomplete": "current-password",
        })
    )

    def clean(self):
        cleaned_data = super().clean()

        tipo_documento = cleaned_data.get("tipo_documento")
        numero_documento = cleaned_data.get("numero_documento")

        if tipo_documento and numero_documento:
            Usuario = get_user_model()

            coincide_otro_tipo = Usuario.objects.filter(
                numero_documento=numero_documento
            ).exclude(
                tipo_documento=tipo_documento
            ).exists()

            if coincide_otro_tipo:
                raise forms.ValidationError(
                    "El tipo de documento no coincide con el número ingresado."
                )

        return cleaned_data
