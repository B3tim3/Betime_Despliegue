"""
Renombra Ficha -> Grupo SIN perder datos.

Se escribe a mano con RenameModel / RenameField (en vez de dejar que
makemigrations lo adivine) porque el autodetector podría interpretar el
cambio como "borrar la tabla Ficha y crear Grupo", y eso eliminaría todos
los grupos y los aprendices que dependen de ellos.

Qué cambia en la base de datos:
  usuarios_ficha            -> usuarios_grupo
  ficha.numero_ficha        -> grupo.numero_grupo
  aprendiz.ficha_id         -> aprendiz.grupo_id
También se actualizan los related_name ("fichas" -> "grupos") y las
etiquetas de estado (Activa/Cerrada -> Activo/Cerrado); los valores
guardados ("activa", "cerrada") NO cambian.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0004_genero_telefono_usuario"),
    ]

    operations = [
        migrations.RenameModel(old_name="Ficha", new_name="Grupo"),
        migrations.RenameField(model_name="grupo", old_name="numero_ficha", new_name="numero_grupo"),
        migrations.RenameField(model_name="aprendiz", old_name="ficha", new_name="grupo"),
        migrations.AlterField(
            model_name="grupo",
            name="programa_formacion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="grupos",
                to="usuarios.programaformacion",
            ),
        ),
        migrations.AlterField(
            model_name="grupo",
            name="jornada",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="grupos",
                to="usuarios.jornada",
            ),
        ),
        migrations.AlterField(
            model_name="grupo",
            name="estado",
            field=models.CharField(
                choices=[("activa", "Activo"), ("cerrada", "Cerrado")],
                default="activa",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="usuario",
            name="genero",
            field=models.CharField(
                blank=True,
                choices=[("M", "Masculino"), ("F", "Femenino")],
                default="",
                max_length=1,
            ),
        ),
    ]
