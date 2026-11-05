import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from usuarios.choices import GENERO_CHOICES, TIPO_DOCUMENTO_CHOICES
from usuarios.models import Grupo
from usuarios.services.grupos import GrupoNoDisponible, buscar_grupo_vigente
from usuarios.validators import validar_numero_documento


class RegistroAprendizForm(forms.Form):
    """
    Registro de aprendices. Los campos están en el orden en que se
    muestran en pantalla, en tres bloques:

      1. Datos personales
      2. Grupo  (número de grupo; de él salen programa, jornada y nivel)
      3. Contraseña

    El nivel de formación NO se pide: sale del programa elegido
    (ProgramaFormacion.nivel_formacion). Así no puede haber un aprendiz
    con un "Tecnólogo" asignado a un programa "Técnico".
    """

    # ---------- 1. Datos personales ----------

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

    tipo_documento = forms.ChoiceField(
        choices=[("", "Selecciona")] + list(TIPO_DOCUMENTO_CHOICES),
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

    genero = forms.ChoiceField(
        choices=[("", "Selecciona")] + list(GENERO_CHOICES),
        label="Género",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
        })
    )

    telefono = forms.CharField(
        label="Teléfono de contacto",
        max_length=20,   # admite espacios y guiones al escribir; se guarda limpio (máx. 15)
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "autocomplete": "tel",
            "inputmode": "tel",
            "placeholder": "Ej. 3001234567",
        })
    )

    # ---------- 2. Grupo ----------
    # El aprendiz escribe su número de grupo (ficha). El programa, la jornada y el nivel
    # salen del grupo: no hay tres listas que recorrer ni forma de combinarlos mal.

    numero_grupo = forms.CharField(
        label="Número de grupo",
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "id": "id_numero_grupo",
            "inputmode": "numeric",
            "autocomplete": "off",
            "placeholder": "Ej. 2900001",
        })
    )

    # ---------- 3. Contraseña ----------

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

    # Bloques que usa la plantilla para armar los pasos.
    PASOS = {
        1: ["nombres", "apellidos", "tipo_documento", "numero_documento",
            "genero", "email", "telefono"],
        2: ["numero_grupo"],
        3: ["password", "password_confirm"],
    }

    @property
    def hay_grupos_vigentes(self):
        return Grupo.objects.vigentes().exists()

    # ---------- Validaciones de campo ----------

    def clean_nombres(self):
        return " ".join(self.cleaned_data["nombres"].split())

    def clean_apellidos(self):
        return " ".join(self.cleaned_data["apellidos"].split())

    def clean_numero_documento(self):
        numero_documento = validar_numero_documento(
            self.cleaned_data.get("tipo_documento"), self.cleaned_data["numero_documento"]
        )

        Usuario = get_user_model()
        if Usuario.objects.filter(numero_documento=numero_documento).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este número de documento."
            )

        return numero_documento

    def clean_numero_grupo(self):
        try:
            self._grupo = buscar_grupo_vigente(self.cleaned_data["numero_grupo"])
        except GrupoNoDisponible as error:
            raise forms.ValidationError(str(error))
        return self._grupo.numero_grupo

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        Usuario = get_user_model()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo electrónico."
            )

        return email

    def clean_telefono(self):
        # Acepta "300 123 4567", "300-123-4567" o "+57 300 123 4567":
        # se quitan separadores y se guarda solo lo esencial.
        telefono = re.sub(r"[\s\-().]", "", self.cleaned_data["telefono"])

        if not re.fullmatch(r"\+?\d{7,13}", telefono):
            raise forms.ValidationError(
                "Ingresa un número de teléfono válido (solo números, entre 7 y 13 dígitos)."
            )

        return telefono

    def clean_password(self):
        password = self.cleaned_data.get("password")
        validate_password(password)
        return password

    # ---------- Validación cruzada ----------

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Las contraseñas no coinciden.")

        # El grupo se resolvió (y se comprobó que sigue vigente) en clean_numero_grupo.
        if getattr(self, "_grupo", None) is not None and "numero_grupo" in cleaned_data:
            cleaned_data["grupo"] = self._grupo

        return cleaned_data

    # ---------- Ayudas para la plantilla ----------

    def campos_del_paso(self, numero):
        return [self[nombre] for nombre in self.PASOS[numero]]

    def paso_con_errores(self):
        """Primer paso que contiene algún error (para abrir ese paso al recargar)."""
        for numero, campos in self.PASOS.items():
            if any(self.errors.get(nombre) for nombre in campos):
                return numero
        return 1
