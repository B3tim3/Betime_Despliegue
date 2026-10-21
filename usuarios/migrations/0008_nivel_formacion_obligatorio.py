"""
Paso 3 de 3: elimina el texto viejo y deja el campo definitivo.

Quita la columna de texto "nivel_formacion", renombra la columna
temporal "nivel" a "nivel_formacion" y la vuelve obligatoria.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0007_migrar_niveles"),
    ]

    operations = [
        migrations.RemoveField(model_name="programaformacion", name="nivel_formacion"),
        migrations.RenameField(model_name="programaformacion", old_name="nivel", new_name="nivel_formacion"),
        migrations.AlterField(
            model_name="programaformacion",
            name="nivel_formacion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="programas",
                to="usuarios.nivelformacion",
                verbose_name="nivel de formación",
            ),
        ),
    ]
