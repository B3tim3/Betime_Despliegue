from django import forms

from core.forms_imagenes import ValidaImagenesMixin
from core.widgets import FlatpickrDateTimeInput
from actividades.models import Actividad


class ActividadForm(ValidaImagenesMixin, forms.ModelForm):

    # El estado ya NO se elige entre cuatro: programado / en curso / finalizado
    # se calculan solos con las fechas. Aquí solo se decide si la actividad está
    # cancelado. Es un CharField (con un Select de dos opciones) para seguir
    # aceptando cualquier valor viejo que llegue; clean_estado lo normaliza.
    estado = forms.CharField(
        label="Estado",
        required=False,
        widget=forms.Select(
            choices=[("", "Automático (según las fechas)"), ("cancelado", "Cancelada")],
            attrs={"class": "form-select"},
        ),
        help_text=(
            "Cambia solo: Programada antes de iniciar, En curso mientras ocurre y "
            "Finalizada después. Marca «Cancelada» solo si la actividad no se va a realizar."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["estado"] = "cancelado" if getattr(self.instance, "estado", "") == "cancelado" else ""

    def clean_estado(self):
        # Cualquier cosa que no sea "cancelado" significa "automático"; el modelo
        # calcula el estado real al guardar (Actividad.save).
        return "cancelado" if self.cleaned_data.get("estado") == "cancelado" else "programado"

    class Meta:
        model = Actividad
        fields = [
            "titulo",
            "descripcion",
            "lugar",
            "horas_otorgadas",
            "cupo_maximo",
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
            "cupo_maximo": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "Sin límite"}),
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "fecha_inicio": FlatpickrDateTimeInput(),
            "fecha_fin": FlatpickrDateTimeInput(),
        }

    def clean(self):
        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            self.add_error("fecha_fin", "La fecha de fin debe ser posterior a la fecha de inicio.")

        # No se puede dejar un cupo menor a los que ya están inscritos: quedarían
        # aprendices "de más" que ya tienen su lugar confirmado.
        cupo = cleaned_data.get("cupo_maximo")
        if cupo is not None and self.instance.pk:
            inscritos = self.instance.inscripciones.exclude(estado="cancelada").count()
            if cupo < inscritos:
                self.add_error(
                    "cupo_maximo",
                    f"Ya hay {inscritos} aprendices inscritos; el cupo no puede ser menor. "
                    "Déjalo en el mismo número o más, o vacío para quitar el límite.",
                )

        return cleaned_data
