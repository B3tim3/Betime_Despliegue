"""
Tablas (django-tables2) para las listas del panel.

Una Table describe, como clase, qué columnas mostrar y cómo ordenar
cada una — reemplaza el <table> escrito a mano + el ordenar-por-clic
en JS que teníamos antes. El orden por columna aquí sí pasa por la
base de datos (ORDER BY real), a diferencia del JS anterior que solo
reordenaba las filas ya cargadas en el navegador.
"""

import django_tables2 as tables
from django.utils.html import format_html

from usuarios.models import Aprendiz


class AprendizTable(tables.Table):

    nombre = tables.Column(
        accessor="usuario",
        verbose_name="Nombre",
        order_by=("usuario__apellidos", "usuario__nombres"),
    )
    documento = tables.Column(
        accessor="usuario__numero_documento",
        verbose_name="Documento",
    )
    contacto = tables.Column(
        accessor="usuario__email",
        verbose_name="Contacto",
        orderable=False,
        empty_values=(),
    )
    grupo = tables.Column(
        accessor="grupo__numero_grupo",
        verbose_name="Grupo",
    )
    programa = tables.Column(
        accessor="grupo__programa_formacion__nombre",
        verbose_name="Programa",
    )
    estado = tables.Column(verbose_name="Estado")
    acciones = tables.TemplateColumn(
        verbose_name="Acciones",
        orderable=False,
        template_code=(
            '<a href="{% url \'usuarios:aprendices_editar\' record.id %}" '
            'class="btn btn-sm btn-outline-success">Editar</a> '
            '<form method="post" action="{% url \'usuarios:aprendices_eliminar\' record.id %}" '
            'class="d-inline" '
            'data-confirmar-eliminar="¿Eliminar a {{ record.usuario.get_full_name }}? '
            'Esto borra su cuenta y no se puede deshacer.">'
            '{% csrf_token %}'
            '<button type="submit" class="btn btn-sm btn-outline-danger">Eliminar</button>'
            '</form>'
        ),
    )

    class Meta:
        model = Aprendiz
        fields = ("nombre", "documento", "contacto", "grupo", "programa", "estado", "acciones")
        attrs = {"class": "table align-middle bg-white"}
        order_by = ("usuario__apellidos",)

    def render_nombre(self, value):
        return value.get_full_name()

    def render_documento(self, value, record):
        return f"{record.usuario.tipo_documento} {value}"

    def render_contacto(self, record):
        usuario = record.usuario
        if not usuario.email and not usuario.telefono:
            return format_html('<span class="text-muted">Sin datos</span>')
        return format_html(
            '<div class="small">{}</div><div class="small text-muted">{}</div>',
            usuario.email or "—", usuario.telefono or "—",
        )

    def render_estado(self, record):
        colores = {"activo": "success", "retirado": "secondary", "egresado": "info"}
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            colores.get(record.estado, "light"), record.get_estado_display(),
        )
