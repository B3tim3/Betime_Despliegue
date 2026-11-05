"""
Lista las cuentas cuyo número de documento NO cumple la regla actual (usuarios/validators.py).

Solo LEE: no cambia nada. Sirve para encontrar cuentas creadas antes de que existiera la
validación (por ejemplo, alguien que escribió su correo en el campo del documento) y
corregirlas desde Aprendices -> Editar. Esas cuentas siguen pudiendo iniciar sesión.

    python manage.py revisar_documentos
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from usuarios.validators import documento_es_valido


class Command(BaseCommand):
    help = "Lista las cuentas con número de documento inválido (solo lectura)."

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        malas = [
            u for u in Usuario.objects.order_by("id").only("id", "tipo_documento", "numero_documento", "nombres", "apellidos")
            if not documento_es_valido(u.tipo_documento, u.numero_documento)
        ]
        if not malas:
            self.stdout.write(self.style.SUCCESS("Todos los números de documento son válidos."))
            return
        self.stdout.write(f"Cuentas con documento inválido: {len(malas)}")
        for u in malas:
            self.stdout.write(f"  #{u.id}  {u.tipo_documento} «{u.numero_documento}»  {u.get_full_name()}")
        self.stdout.write("Corrígelas desde el panel: Aprendices -> Editar.")
