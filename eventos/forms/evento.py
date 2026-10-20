from django import forms

from core.widgets import FlatpickrDateTimeInput
from eventos.models import Evento


class EventoForm(forms.ModelForm):

    class Meta:
        model = Evento
        fields = [
            "titulo",
            "descripcion",
            "lugar",
            "horas_otorgadas",
            "imagen",
            "fecha_inicio",
            "fecha_fin",
            "estado",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "lugar": forms.TextInput(attrs={"class": "form-control"}),
            "horas_otorgadas": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "fecha_inicio": FlatpickrDateTimeInput(),
            "fecha_fin": FlatpickrDateTimeInput(),
            "estado": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            self.add_error("fecha_fin", "La fecha de fin debe ser posterior a la fecha de inicio.")

        return cleaned_data
