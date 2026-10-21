from django import forms

from usuarios.models import Aprendiz, Grupo, Jornada, NivelFormacion, ProgramaFormacion


class ProgramaFormacionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nivel_formacion"].empty_label = "Selecciona el nivel de formación"
        self.fields["nivel_formacion"].help_text = (
            "Si el nivel que necesitas no aparece, créalo primero en Niveles de formación."
        )

    class Meta:
        model = ProgramaFormacion
        fields = ["nombre", "codigo", "nivel_formacion", "duracion_meses", "estado"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nivel_formacion": forms.Select(attrs={"class": "form-select"}),
            "duracion_meses": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activo", "Activo"),
                ("inactivo", "Inactivo"),
            ]),
        }


class NivelFormacionForm(forms.ModelForm):

    class Meta:
        model = NivelFormacion
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Técnico, Tecnólogo..."}),
        }

    def clean_nombre(self):
        # El campo es unique, pero distingue mayúsculas: "técnico" y
        # "Técnico" serían dos niveles distintos. Aquí se evita.
        nombre = " ".join(self.cleaned_data["nombre"].split())

        repetidos = NivelFormacion.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetidos = repetidos.exclude(pk=self.instance.pk)

        if repetidos.exists():
            raise forms.ValidationError("Ya existe un nivel de formación con ese nombre.")

        return nombre


class JornadaForm(forms.ModelForm):

    class Meta:
        model = Jornada
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Diurna, Nocturna, Mixta..."}),
        }


class GrupoForm(forms.ModelForm):

    class Meta:
        model = Grupo
        fields = ["programa_formacion", "numero_grupo", "jornada", "fecha_inicio", "fecha_fin", "estado"]
        widgets = {
            "programa_formacion": forms.Select(attrs={"class": "form-select"}),
            "numero_grupo": forms.TextInput(attrs={"class": "form-control"}),
            "jornada": forms.Select(attrs={"class": "form-select"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activa", "Activo"),
                ("cerrada", "Cerrado"),
            ]),
        }

    def clean(self):
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            self.add_error("fecha_fin", "La fecha de fin debe ser posterior a la fecha de inicio.")

        return cleaned_data


class AprendizEstadoForm(forms.ModelForm):
    """
    Un aprendiz se crea a través del registro público, no desde este panel.
    Aquí Bienestar solo puede reasignar su grupo o cambiar su estado
    (activo, retirado, egresado).
    """

    class Meta:
        model = Aprendiz
        fields = ["grupo", "estado"]
        widgets = {
            "grupo": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activo", "Activo"),
                ("retirado", "Retirado"),
                ("egresado", "Egresado"),
            ]),
        }
