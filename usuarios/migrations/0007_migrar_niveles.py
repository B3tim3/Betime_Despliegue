"""
Paso 2 de 3: copia los niveles escritos como texto a la nueva tabla.

- Agrupa variantes del mismo nivel ("tecnologo", "Tecnólogo ",
  "TECNÓLOGO") en un solo registro.
- Siempre deja creados "Técnico" y "Tecnólogo" para que el catálogo no
  quede vacío en una base nueva (se pueden editar o quitar después).
- Un programa sin nivel escrito queda en "Sin definir".
"""

import unicodedata
from collections import Counter

from django.db import migrations

BASE = ["Técnico", "Tecnólogo"]
PREFERIDOS = {"tecnico": "Técnico", "tecnologo": "Tecnólogo"}


def _clave(texto):
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.casefold().split())


def copiar_niveles(apps, schema_editor):
    Programa = apps.get_model("usuarios", "ProgramaFormacion")
    Nivel = apps.get_model("usuarios", "NivelFormacion")

    for nombre in BASE:
        Nivel.objects.get_or_create(nombre=nombre)

    # Nombre "bonito" de cada clave: el preferido si existe, si no la
    # variante más frecuente tal como se escribió.
    variantes = {}
    for texto in Programa.objects.values_list("nivel_formacion", flat=True):
        limpio = " ".join((texto or "").split())
        if limpio:
            variantes.setdefault(_clave(limpio), Counter())[limpio] += 1

    por_clave = {}
    for clave, conteo in variantes.items():
        nombre = PREFERIDOS.get(clave) or conteo.most_common(1)[0][0]
        nivel, _ = Nivel.objects.get_or_create(nombre=nombre)
        por_clave[clave] = nivel

    sin_definir = None
    for programa in Programa.objects.all():
        limpio = " ".join((programa.nivel_formacion or "").split())
        if limpio:
            nivel = por_clave[_clave(limpio)]
        else:
            if sin_definir is None:
                sin_definir, _ = Nivel.objects.get_or_create(nombre="Sin definir")
            nivel = sin_definir
        programa.nivel_id = nivel.id
        programa.save(update_fields=["nivel"])


def devolver_texto(apps, schema_editor):
    Programa = apps.get_model("usuarios", "ProgramaFormacion")
    for programa in Programa.objects.select_related("nivel"):
        if programa.nivel_id:
            programa.nivel_formacion = programa.nivel.nombre
            programa.save(update_fields=["nivel_formacion"])


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0006_nivelformacion"),
    ]

    operations = [
        migrations.RunPython(copiar_niveles, devolver_texto),
    ]
