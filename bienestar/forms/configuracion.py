from django import forms

from bienestar.models import ConfiguracionBienestar


class ConfiguracionBienestarForm(forms.ModelForm):

    class Meta:
        model = ConfiguracionBienestar
        fields = ["meta_horas"]
        widgets = {
            "meta_horas": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 1000}),
        }
