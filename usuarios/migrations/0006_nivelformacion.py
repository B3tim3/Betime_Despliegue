"""
Paso 1 de 3 para convertir el nivel de formación en un catálogo editable.

Crea la tabla NivelFormacion y agrega a los programas una columna
temporal "nivel" (puede quedar vacía). Los pasos siguientes copian los
niveles de texto que ya existen y cambian el campo definitivo. Se hace
en 3 migraciones separadas (estructura / datos / estructura) porque
mezclar cambios de estructura y de datos en una sola transacción puede
fallar en PostgreSQL.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0005_ficha_a_grupo"),
    ]

    operations = [
        migrations.CreateModel(
            name="NivelFormacion",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=60, unique=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Nivel de formación",
                "verbose_name_plural": "Niveles de formación",
                "ordering": ["nombre"],
            },
        ),
        migrations.AddField(
            model_name="programaformacion",
            name="nivel",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="usuarios.nivelformacion",
            ),
        ),
    ]
