import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from usuarios.choices import GENERO_CHOICES, TIPO_DOCUMENTO_CHOICES
from usuarios.models import Ficha, Jornada, ProgramaFormacion


class RegistroAprendizForm(forms.Form):
    """
    Registro de aprendices. Los campos están en el orden en que se
    muestran en pantalla, en tres bloques:

      1. Datos personales
      2. Programa de formación  (programa -> jornada -> grupo)
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

    # ---------- 2. Programa de formación ----------

    programa_formacion = forms.ModelChoiceField(
        queryset=ProgramaFormacion.objects.filter(estado="activo").order_by("nombre"),
        label="Programa de formación",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_programa_formacion",
        }),
        empty_label="Selecciona tu programa de formación"
    )

    jornada = forms.ModelChoiceField(
        queryset=Jornada.objects.none(),
        label="Jornada de formación",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_jornada",
        }),
        empty_label="Selecciona primero tu programa de formación"
    )

    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.none(),
        label="Número de grupo",
        widget=forms.Select(attrs={
            "class": "form-select",
            "id": "id_ficha",
        }),
        empty_label="Selecciona primero tu jornada"
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
        2: ["programa_formacion", "jornada", "ficha"],
        3: ["password", "password_confirm"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Los <select> de jornada y grupo empiezan vacíos y se llenan por
        # JavaScript. Al reenviar el POST (por ejemplo tras un error de
        # validación) los llenamos aquí con lo que corresponde al programa
        # y la jornada ya elegidos, para que la opción enviada siga siendo
        # válida y el formulario no pierda lo que la persona seleccionó.
        programa_id = self.data.get("programa_formacion") if self.data else None
        jornada_id = self.data.get("jornada") if self.data else None

        if programa_id and str(programa_id).isdigit():
            self.fields["jornada"].queryset = Jornada.objects.filter(
                fichas__programa_formacion_id=programa_id,
                fichas__estado="activa",
            ).distinct().order_by("nombre")

            if jornada_id and str(jornada_id).isdigit():
                self.fields["ficha"].queryset = Ficha.objects.filter(
                    programa_formacion_id=programa_id,
                    jornada_id=jornada_id,
                    estado="activa",
                ).order_by("numero_ficha")

    # ---------- Validaciones de campo ----------

    def clean_nombres(self):
        return " ".join(self.cleaned_data["nombres"].split())

    def clean_apellidos(self):
        return " ".join(self.cleaned_data["apellidos"].split())

    def clean_numero_documento(self):
        numero_documento = self.cleaned_data["numero_documento"].strip()

        Usuario = get_user_model()
        if Usuario.objects.filter(numero_documento=numero_documento).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este número de documento."
            )

        return numero_documento

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

        # Defensa en el servidor: aunque el <select> filtre por JavaScript,
        # alguien podría enviar a mano un grupo que no corresponde. Se
        # comprueba que el grupo realmente pertenezca al programa y a la
        # jornada elegidos, y que siga activo.
        programa = cleaned_data.get("programa_formacion")
        jornada = cleaned_data.get("jornada")
        ficha = cleaned_data.get("ficha")

        if programa and jornada and ficha:
            if (
                ficha.programa_formacion_id != programa.id
                or ficha.jornada_id != jornada.id
                or ficha.estado != "activa"
            ):
                self.add_error(
                    "ficha",
                    "El grupo seleccionado no corresponde al programa y la jornada elegidos."
                )

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
