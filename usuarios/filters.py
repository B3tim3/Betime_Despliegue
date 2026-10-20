"""
Filtros (django-filter) para las listas del panel.

Un FilterSet describe, como clase, qué se puede filtrar de un
queryset a partir de los parámetros ?q=...&estado=... de la URL — es
el reemplazo, del lado del servidor, de los Q() que antes armábamos a
mano en cada vista de exportar. La misma clase se usa tanto para la
tabla en pantalla como para exportar, así ambas quedan sincronizadas
por diseño (no hay dos lugares con la lógica de búsqueda repetida).
"""

import django_filters
from django import forms
from django.db.models import Q

from usuarios.choices import TIPO_DOCUMENTO_CHOICES
from usuarios.models import Aprendiz
from usuarios.models.aprendiz import ESTADO_CHOICES as APRENDIZ_ESTADO_CHOICES


class AprendizFilter(django_filters.FilterSet):

    q = django_filters.CharFilter(
        method="buscar_texto",
        label="",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Buscar por nombre, documento o ficha...",
        }),
    )

    tipo_documento = django_filters.ChoiceFilter(
        field_name="usuario__tipo_documento",
        choices=TIPO_DOCUMENTO_CHOICES,
        empty_label="Todos los tipos de documento",
        label="",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    estado = django_filters.ChoiceFilter(
        choices=APRENDIZ_ESTADO_CHOICES,
        empty_label="Todos los estados",
        label="",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Aprendiz
        fields = []  # sin autogenerar nada: solo los filtros de arriba

    def buscar_texto(self, queryset, name, value):
        return queryset.filter(
            Q(usuario__nombres__icontains=value) |
            Q(usuario__apellidos__icontains=value) |
            Q(usuario__numero_documento__icontains=value) |
            Q(usuario__tipo_documento__icontains=value) |
            Q(ficha__numero_ficha__icontains=value)
        )
