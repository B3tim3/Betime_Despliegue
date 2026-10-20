from django import forms

from bienestar.models import MiembroBienestar


class MiembroBienestarForm(forms.ModelForm):

    class Meta:
        model = MiembroBienestar
        fields = [
            "nombre",
            "cargo",
            "categoria",
            "descripcion",
            "foto",
            "correo_asesorias",
            "estado",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "foto": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "correo_asesorias": forms.EmailInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("activo", "Activo"),
                ("inactivo", "Inactivo"),
            ]),
        }
