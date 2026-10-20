from django import forms

from usuarios.models import Aprendiz, Ficha, Jornada, ProgramaFormacion


class ProgramaFormacionForm(forms.ModelForm):

    class Meta:
        model = ProgramaFormacion
        fields = ["nombre", "codigo", "nivel_formacion", "duracion_meses", "estado"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nivel_formacion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Técnico, Tecnólogo..."}),
            "duracion_meses": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activo", "Activo"),
                ("inactivo", "Inactivo"),
            ]),
        }


class JornadaForm(forms.ModelForm):

    class Meta:
        model = Jornada
        fields = ["nombre"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Diurna, Nocturna, Mixta..."}),
        }


class FichaForm(forms.ModelForm):

    class Meta:
        model = Ficha
        fields = ["programa_formacion", "numero_ficha", "jornada", "fecha_inicio", "fecha_fin", "estado"]
        widgets = {
            "programa_formacion": forms.Select(attrs={"class": "form-select"}),
            "numero_ficha": forms.TextInput(attrs={"class": "form-control"}),
            "jornada": forms.Select(attrs={"class": "form-select"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activa", "Activa"),
                ("cerrada", "Cerrada"),
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
    Aquí Bienestar solo puede reasignar su ficha o cambiar su estado
    (activo, retirado, egresado).
    """

    class Meta:
        model = Aprendiz
        fields = ["ficha", "estado"]
        widgets = {
            "ficha": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activo", "Activo"),
                ("retirado", "Retirado"),
                ("egresado", "Egresado"),
            ]),
        }
