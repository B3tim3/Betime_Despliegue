"""
python manage.py limpiar_datos [--dry-run] [--dias-notificaciones 90] [--horas-intentos 24]

Mantenimiento para que las tablas que crecen sin parar no se coman la base de datos:
  * Intentos fallidos de acceso de más de 24 h (solo sirven para el bloqueo temporal).
  * Notificaciones YA LEÍDAS de más de 90 días. Las no leídas NUNCA se borran.
No toca la auditoría (su valor es precisamente que no se borra).
Pensado para ejecutarse cada semana (a mano o con un cron).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notificaciones.models import Notificacion
from usuarios.models import IntentoFallido


class Command(BaseCommand):
    help = "Borra intentos de acceso viejos y notificaciones leídas antiguas."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo cuenta, no borra.")
        parser.add_argument("--dias-notificaciones", type=int, default=90)
        parser.add_argument("--horas-intentos", type=int, default=24)

    def handle(self, *args, dry_run=False, dias_notificaciones=90, horas_intentos=24, **opciones):
        ahora = timezone.now()
        intentos = IntentoFallido.objects.filter(fecha__lt=ahora - timedelta(hours=horas_intentos))
        notificaciones = Notificacion.objects.filter(
            leida=True, fecha_creacion__lt=ahora - timedelta(days=dias_notificaciones))

        n_int, n_not = intentos.count(), notificaciones.count()
        if not dry_run:
            intentos.delete()
            notificaciones.delete()

        prefijo = "[SIMULACIÓN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefijo}Intentos fallidos {'a borrar' if dry_run else 'borrados'}: {n_int} (más de {horas_intentos} h)"))
        self.stdout.write(self.style.SUCCESS(
            f"{prefijo}Notificaciones leídas {'a borrar' if dry_run else 'borradas'}: {n_not} (más de {dias_notificaciones} días)"))
