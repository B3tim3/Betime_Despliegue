from django import forms

from core.forms_imagenes import ValidaImagenesMixin

from publicaciones.models import Publicacion


class PublicacionForm(ValidaImagenesMixin, forms.ModelForm):

    class Meta:
        model = Publicacion
        fields = [
            "titulo",
            "contenido",
            "imagen",
            "estado",
        ]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "contenido": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}, choices=[
                ("borrador", "Borrador"),
                ("publicado", "Publicado"),
            ]),
        }
