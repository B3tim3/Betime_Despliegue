"""
Widgets compartidos para el proyecto.

1. AdminSplitDateTimeSinSegundos — para ModelAdmin de Django admin.
2. DateTimeLocalInput — para formularios propios del panel (ModelForm)
   que usan <input type="datetime-local">.

Django admin, por defecto, muestra el campo de hora con segundos
(HH:MM:SS) en cualquier DateTimeField. En Be Time no se usan los
segundos en ningún lado, así que estos widgets reemplazan los que
Django trae por defecto por unos idénticos pero sin esa casilla.

Uso típico en un ModelAdmin:

    from django.db import models
    from core.widgets import AdminSplitDateTimeSinSegundos

    class EventoAdmin(admin.ModelAdmin):
        formfield_overrides = {
            models.DateTimeField: {"widget": AdminSplitDateTimeSinSegundos},
        }

Uso típico en un ModelForm:

    from core.widgets import DateTimeLocalInput

    class EventoForm(forms.ModelForm):
        class Meta:
            widgets = {
                "fecha_inicio": DateTimeLocalInput(attrs={"class": "form-control"}),
            }
"""

from django import forms
from django.contrib.admin.widgets import AdminDateWidget, AdminSplitDateTime, AdminTimeWidget


class AdminSplitDateTimeSinSegundos(AdminSplitDateTime):
    """Igual al selector de fecha/hora del admin, pero sin segundos."""

    def __init__(self, attrs=None):
        widgets = [AdminDateWidget, AdminTimeWidget(format="%H:%M")]
        # Se llama al __init__ de MultiWidget directamente (saltando el
        # de AdminSplitDateTime) porque es el que arma esta lista de
        # widgets; así reemplazamos el AdminTimeWidget por defecto por
        # uno con el formato que sí queremos.
        forms.MultiWidget.__init__(self, widgets, attrs)


class DateTimeLocalInput(forms.DateTimeInput):
    """
    Input HTML5 <input type="datetime-local"> que garantiza mostrar
    solo hasta minutos (sin segundos).

    No basta con pasarle format="%Y-%m-%dT%H:%M" al DateTimeInput normal
    de Django: por debajo, Django a veces usa su propio sistema de
    formatos "localizados" e ignora ese format, y el value que termina
    en el HTML sí trae segundos (aunque no se vean) — y algunos
    navegadores (Edge/Chrome en Windows) muestran igual el selector de
    segundos con solo detectar que el valor los trae.

    Por eso aquí se sobreescribe format_value() directamente: así el
    texto que se manda al HTML nunca tiene segundos, sin importar lo
    que Django hubiera decidido usar por su cuenta.

    NOTA: en la práctica es mejor usar FlatpickrDateTimeInput (más
    abajo) — este widget se deja aquí solo por si algún día quieren
    volver al selector nativo del navegador sin depender de JS externo.
    """

    input_type = "datetime-local"

    def format_value(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            # Ya viene como texto (por ejemplo, si el formulario se
            # está re-mostrando después de un error de validación).
            return value
        return value.strftime("%Y-%m-%dT%H:%M")


class FlatpickrDateTimeInput(forms.DateTimeInput):
    """
    Input de fecha y hora que usa Flatpickr (JS, cargado en
    base_private.html) en vez del selector nativo <input
    type="datetime-local"> del navegador.

    Por qué: el selector nativo se comporta distinto según el
    navegador (en Edge/Chrome en Windows mostraba segundos aunque se
    le pidiera que no). Flatpickr dibuja su propio calendario/reloj
    con JS, así que se ve y se comporta igual sin importar el
    navegador — ya no dependemos de cómo cada uno interprete el HTML5
    datetime-local.

    Cómo funciona: este widget solo pone la clase CSS
    "flatpickr-fecha-hora" en un <input type="text"> normal.
    static/js/flatpickr-init.js es el que busca esa clase y le activa
    Flatpickr encima — el widget de Python no sabe nada de JS, solo dej
    la "marca" para que el script lo encuentre (mismo patrón que
    data-tabla-filtro en tabla-filtro.js).
    """

    input_type = "text"

    def __init__(self, attrs=None):
        default_attrs = {"class": "form-control flatpickr-fecha-hora", "autocomplete": "off"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format="%Y-%m-%d %H:%M")

    def format_value(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            return value
        return value.strftime("%Y-%m-%d %H:%M")
