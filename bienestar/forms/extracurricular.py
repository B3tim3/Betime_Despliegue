from django import forms

from bienestar.models import ActividadExtracurricular


class ActividadExtracurricularForm(forms.ModelForm):

    class Meta:
        model = ActividadExtracurricular
        fields = ["titulo", "descripcion", "horas", "fecha"]
        labels = {
            "titulo": "Título",
            "descripcion": "Descripción",
            "horas": "Horas por aprendiz",
            "fecha": "Fecha",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "form-control", "maxlength": 150,
                "placeholder": "Ej.: Buen porte del uniforme"}),
            "descripcion": forms.Textarea(attrs={
                "class": "form-control", "rows": 3,
                "placeholder": "Por qué se dan estas horas (opcional)"}),
            "horas": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 40}),
            "fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
        }

    def clean_horas(self):
        horas = self.cleaned_data["horas"]
        if horas < 1 or horas > 40:
            raise forms.ValidationError("Las horas deben estar entre 1 y 40.")
        return horas
