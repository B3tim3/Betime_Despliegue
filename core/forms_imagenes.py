from django import forms
from django.core.files.uploadedfile import UploadedFile

from core.services.imagenes import validar_peso


class ValidaImagenesMixin:
    """
    Para formularios con ImageField: rechaza imágenes nuevas de más de 5 MB con un
    mensaje claro (junto al campo), antes de guardar nada. Poner como PRIMERA base.
    """

    def clean(self):
        datos = super().clean()
        for nombre, campo in self.fields.items():
            if isinstance(campo, forms.ImageField):
                valor = (datos or {}).get(nombre)
                if isinstance(valor, UploadedFile):   # solo lo recién subido, no la imagen ya guardada
                    try:
                        validar_peso(valor)
                    except forms.ValidationError as error:
                        self.add_error(nombre, error)
        return datos
