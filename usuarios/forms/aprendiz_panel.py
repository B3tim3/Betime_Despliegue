"""
Corrección de los datos de un aprendiz por el personal de Bienestar
(Panel -> Aprendices -> Editar).

Un aprendiz se crea por el registro público y solo puede cambiar sus datos de
contacto desde "Mi perfil". Cuando se equivoca en el documento, el nombre o
el grupo, Bienestar los corrige aquí. Por eso este formulario SÍ permite
cambiar el documento (con el que la persona inicia sesión), y avisa de ello.

Edita dos tablas a la vez: Usuario (identidad y contacto) y Aprendiz (grupo y
estado). Se guardan juntas, en una transacción: o cambia todo o no cambia nada.
"""

import re

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from usuarios.choices import GENERO_CHOICES, TIPO_DOCUMENTO_CHOICES
from usuarios.models import Aprendiz, Grupo
from usuarios.models.aprendiz import ESTADO_CHOICES


class AprendizPanelForm(forms.ModelForm):

    # ---------- Datos del Usuario ----------

    tipo_documento = forms.ChoiceField(
        label="Tipo de documento", choices=TIPO_DOCUMENTO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    numero_documento = forms.CharField(
        label="Número de documento", max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric"}),
        help_text="Es con el que la persona inicia sesión: si lo cambias, deberá usar el número nuevo.",
    )
    nombres = forms.CharField(
        label="Nombres", max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    apellidos = forms.CharField(
        label="Apellidos", max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    genero = forms.ChoiceField(
        label="Género", required=False,
        choices=[("", "Sin dato")] + list(GENERO_CHOICES),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    email = forms.EmailField(
        label="Correo electrónico", required=False,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        label="Teléfono de contacto", required=False, max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel"}),
    )

    # Los campos que viven en Usuario (el resto vive en Aprendiz).
    CAMPOS_USUARIO = (
        "tipo_documento", "numero_documento", "nombres", "apellidos",
        "genero", "email", "telefono",
    )

    class Meta:
        model = Aprendiz
        fields = ["grupo", "estado"]
        widgets = {
            "grupo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=ESTADO_CHOICES),
        }
        labels = {"grupo": "Grupo", "estado": "Estado del aprendiz"}

    # Orden en que se muestran (los de Usuario primero, luego grupo y estado).
    field_order = [*CAMPOS_USUARIO, "grupo", "estado"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = self.instance.usuario

        for campo in self.CAMPOS_USUARIO:
            self.initial[campo] = getattr(self.usuario, campo) or ""

        # Cada opción de grupo muestra su programa y su jornada para no
        # equivocarse al reasignar (hay grupos con el mismo número en jornadas distintas).
        self.fields["grupo"].queryset = Grupo.objects.select_related(
            "programa_formacion", "jornada"
        ).order_by("numero_grupo")
        self.fields["grupo"].label_from_instance = lambda g: (
            f"{g.numero_grupo} — {g.programa_formacion.nombre} · {g.jornada.nombre}"
            + ("" if g.estado == "activa" else f" ({g.get_estado_display()})")
        )

    # ---------- Validaciones ----------

    def clean_nombres(self):
        return " ".join(self.cleaned_data["nombres"].split())

    def clean_apellidos(self):
        return " ".join(self.cleaned_data["apellidos"].split())

    def clean_numero_documento(self):
        numero = self.cleaned_data["numero_documento"].strip()
        if not numero:
            raise forms.ValidationError("Escribe el número de documento.")
        Usuario = get_user_model()
        if Usuario.objects.filter(numero_documento=numero).exclude(pk=self.usuario.pk).exists():
            raise forms.ValidationError("Ya existe otra cuenta con este número de documento.")
        return numero

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if not email:
            return None   # el campo es único: varios vacíos solo caben como NULL, no como ""
        Usuario = get_user_model()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.usuario.pk).exists():
            raise forms.ValidationError("Ya existe otra cuenta con este correo electrónico.")
        return email

    def clean_telefono(self):
        telefono = re.sub(r"[\s\-().]", "", self.cleaned_data["telefono"])
        if telefono and not re.fullmatch(r"\+?\d{7,13}", telefono):
            raise forms.ValidationError(
                "Ingresa un número de teléfono válido (solo números, entre 7 y 13 dígitos)."
            )
        return telefono

    # ---------- Guardar ----------

    @transaction.atomic
    def save(self, commit=True):
        usuario = self.usuario
        for campo in self.CAMPOS_USUARIO:
            setattr(usuario, campo, self.cleaned_data[campo])
        usuario.save(update_fields=list(self.CAMPOS_USUARIO))
        return super().save(commit=commit)

    # ---------- Para la bitácora ----------

    @staticmethod
    def valores_actuales(aprendiz):
        """Los valores de todos los campos del formulario, tal como están hoy (texto legible)."""
        usuario = aprendiz.usuario
        valores = {c: str(getattr(usuario, c) or "") for c in AprendizPanelForm.CAMPOS_USUARIO}
        valores["grupo"] = str(aprendiz.grupo)
        valores["estado"] = aprendiz.get_estado_display()
        return valores
