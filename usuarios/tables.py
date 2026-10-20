"""
Tablas (django-tables2) para las listas del panel.

Una Table describe, como clase, qué columnas mostrar y cómo ordenar
cada una — reemplaza el <table> escrito a mano + el ordenar-por-clic
en JS que teníamos antes. El orden por columna aquí sí pasa por la
base de datos (ORDER BY real), a diferencia del JS anterior que solo
reordenaba las filas ya cargadas en el navegador.
"""

import django_tables2 as tables

from usuarios.models import Aprendiz


class AprendizTable(tables.Table):

    nombre = tables.Column(
        accessor="usuario",
        verbose_name="Nombre",
        order_by=("usuario__apellidos", "usuario__nombres"),
    )
    tipo_documento = tables.Column(
        accessor="usuario__tipo_documento",
        verbose_name="Tipo",
    )
    documento = tables.Column(
        accessor="usuario__numero_documento",
        verbose_name="Documento",
    )
    ficha = tables.Column(
        accessor="ficha__numero_ficha",
        verbose_name="Ficha",
    )
    programa = tables.Column(
        accessor="ficha__programa_formacion__nombre",
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
        fields = ("nombre", "tipo_documento", "documento", "ficha", "programa", "estado", "acciones")
        attrs = {"class": "table align-middle bg-white"}
        order_by = ("usuario__apellidos",)

    def render_nombre(self, value):
        return value.get_full_name()

    def render_estado(self, record):
        return record.get_estado_display()
