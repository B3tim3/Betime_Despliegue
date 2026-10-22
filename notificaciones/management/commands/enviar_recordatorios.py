from django.core.management.base import BaseCommand

from notificaciones.services.recordatorios import HORAS_POR_DEFECTO, enviar_recordatorios


class Command(BaseCommand):
    help = (
        "Envía (campanita + correo) el recordatorio de los eventos que empiezan "
        "pronto. Cada inscripción se recuerda una sola vez, así que se puede "
        "ejecutar tantas veces como se quiera."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--horas", type=int, default=HORAS_POR_DEFECTO,
            help=f"Recordar eventos que empiezan dentro de las próximas N horas (por defecto {HORAS_POR_DEFECTO}).",
        )
        parser.add_argument(
            "--sin-correo", action="store_true",
            help="Solo crear las notificaciones de la campanita, sin mandar correos.",
        )

    def handle(self, *args, **opciones):
        r = enviar_recordatorios(horas=opciones["horas"], enviar_correo=not opciones["sin_correo"])
        self.stdout.write(self.style.SUCCESS(
            f"Recordatorios: {r['recordatorios']} · correos enviados: {r['correos']} · "
            f"sin correo registrado: {r['sin_correo']} · fallidos: {r['fallidos']}"
        ))
