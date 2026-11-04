from django import forms

from core.forms_imagenes import ValidaImagenesMixin

from bienestar.models import MiembroBienestar


class MiembroBienestarForm(ValidaImagenesMixin, forms.ModelForm):

    class Meta:
        model = MiembroBienestar
        fields = [
            "nombre",
            "cargo",
            "descripcion",
            "foto",
            "correo_asesorias",
            "estado",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "foto": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "correo_asesorias": forms.EmailInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activo", "Activo"),
                ("inactivo", "Inactivo"),
            ]),
        }
