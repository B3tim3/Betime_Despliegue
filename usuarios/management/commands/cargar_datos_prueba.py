"""
Carga unos pocos datos de PRUEBA para ver cómo se ve Be Time:
niveles, jornadas, programas, grupos, cuentas de cada rol y 2 actividades.

Uso:
    python manage.py cargar_datos_prueba

Se puede correr varias veces sin duplicar nada (usa get_or_create).
Por seguridad se niega a correr con DEBUG=False (producción), salvo que se
use --forzar a propósito.

Todas las cuentas de prueba usan la contraseña:  Betime2026*
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from actividades.models import Actividad
from usuarios.models import (
    Administrador, Aprendiz, Grupo, Jornada, NivelFormacion,
    PersonalBienestar, ProgramaFormacion, Usuario,
)

CLAVE = "Betime2026*"

PROGRAMAS = [
    # (nombre, código, nivel, meses)
    ("Análisis y Desarrollo de Software", "P-ADSO", "Tecnólogo", 24),
    ("Gestión Empresarial", "P-GEMP", "Tecnólogo", 24),
    ("Programación de Software", "P-PSOF", "Técnico", 12),
    ("Asistencia Administrativa", "P-ASAD", "Técnico", 12),
]

GRUPOS = [
    # (número, código programa, jornada, estado)
    ("3000001", "P-ADSO", "Diurna", "activa"),
    ("3000002", "P-ADSO", "Nocturna", "activa"),
    ("3000003", "P-GEMP", "Diurna", "activa"),
    ("3000004", "P-PSOF", "Diurna", "activa"),
    ("3000005", "P-PSOF", "Mixta", "activa"),
    ("3000006", "P-ASAD", "Nocturna", "activa"),
    ("2900001", "P-ADSO", "Diurna", "cerrada"),   # grupo cerrado: no debe aparecer en el registro
]

APRENDICES = [
    # (tipo doc, documento, nombres, apellidos, género, teléfono, grupo)
    ("CC", "1000000101", "Juan Camilo", "Rodríguez Peña", "M", "3001110001", "3000001"),
    ("CC", "1000000102", "María Fernanda", "Gómez Ruiz", "F", "3001110002", "3000001"),
    ("TI", "1000000103", "Santiago", "Vargas Mora", "M", "3001110003", "3000002"),
    ("CC", "1000000104", "Laura Valentina", "Ortiz Díaz", "F", "3001110004", "3000002"),
    ("CC", "1000000105", "Andrés Felipe", "Castro León", "M", "3001110005", "3000003"),
    ("CE", "1000000106", "Daniela", "Moreno Ríos", "F", "3001110006", "3000003"),
    ("TI", "1000000107", "Sebastián", "Herrera Soto", "M", "3001110007", "3000004"),
    ("CC", "1000000108", "Camila Andrea", "Jiménez Cruz", "F", "3001110008", "3000004"),
    ("CC", "1000000109", "Carlos Eduardo", "Lozano Pardo", "M", "3001110009", "3000005"),
    ("TI", "1000000110", "Valeria", "Mejía Torres", "F", "3001110010", "3000006"),
]


class Command(BaseCommand):
    help = "Carga datos de prueba (niveles, programas, grupos, usuarios y actividades)."

    def add_arguments(self, parser):
        parser.add_argument("--forzar", action="store_true",
                            help="Permite correrlo aunque DEBUG=False (no recomendado).")

    @transaction.atomic
    def handle(self, *args, **opciones):
        if not settings.DEBUG and not opciones["forzar"]:
            raise CommandError(
                "DEBUG está apagado: parece un entorno de producción. "
                "Estos datos son solo de prueba. Si de verdad quieres cargarlos, usa --forzar."
            )

        hoy = date.today()

        # --- Catálogos ---
        niveles = {n: NivelFormacion.objects.get_or_create(nombre=n)[0]
                   for n in ("Técnico", "Tecnólogo", "Especialización Tecnológica")}
        jornadas = {n: Jornada.objects.get_or_create(nombre=n)[0]
                    for n in ("Diurna", "Nocturna", "Mixta")}

        programas = {}
        for nombre, codigo, nivel, meses in PROGRAMAS:
            programas[codigo] = ProgramaFormacion.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "nivel_formacion": niveles[nivel],
                          "duracion_meses": meses, "estado": "activo"},
            )[0]

        grupos = {}
        for numero, codigo, jornada, estado in GRUPOS:
            grupos[numero] = Grupo.objects.get_or_create(
                numero_grupo=numero,
                defaults={
                    "programa_formacion": programas[codigo],
                    "jornada": jornadas[jornada],
                    "fecha_inicio": hoy - timedelta(days=120) if estado == "activa" else hoy - timedelta(days=900),
                    "fecha_fin": hoy + timedelta(days=500) if estado == "activa" else hoy - timedelta(days=100),
                    "estado": estado,
                },
            )[0]

        # --- Cuentas de personal ---
        admin = self._usuario("900000001", "CC", "Administrador", "Be Time", "admin@betime.test", "M", "3100000001")
        Administrador.objects.get_or_create(usuario=admin, defaults={"fecha_ingreso": hoy})
        admin.is_staff = admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])

        bienestar = self._usuario("900000002", "CC", "Paola", "Ramírez Silva", "bienestar@betime.test", "F", "3100000002")
        PersonalBienestar.objects.get_or_create(
            usuario=bienestar, defaults={"cargo": "Coordinadora de Bienestar", "fecha_ingreso": hoy, "estado": "activo"})

        # --- Aprendices ---
        for tipo, doc, nombres, apellidos, genero, tel, grupo in APRENDICES:
            usuario = self._usuario(doc, tipo, nombres, apellidos,
                                    f"{doc}@aprendiz.test", genero, tel)
            Aprendiz.objects.get_or_create(
                usuario=usuario, defaults={"grupo": grupos[grupo], "fecha_ingreso": hoy})

        # --- Actividades ---
        ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
        for titulo, lugar, horas, dias, duracion in (
            ("Taller de pausas activas", "Auditorio principal", 2, 3, 2),
            ("Torneo de microfútbol", "Cancha múltiple", 4, 7, 4),
        ):
            Actividad.objects.get_or_create(
                titulo=titulo,
                defaults={"descripcion": "Actividad de prueba para ver el diseño.",
                          "lugar": lugar, "horas_otorgadas": horas, "creado_por": bienestar,
                          "fecha_inicio": ahora + timedelta(days=dias),
                          "fecha_fin": ahora + timedelta(days=dias, hours=duracion),
                          "estado": "programado"},
            )

        self.stdout.write(self.style.SUCCESS("Datos de prueba cargados."))
        self.stdout.write(
            "\nCuentas (el usuario es el NÚMERO DE DOCUMENTO) — contraseña de todas: " + CLAVE + "\n"
            "  Administrador: 900000001\n"
            "  Bienestar:     900000002\n"
            "  Aprendices:    1000000101 ... 1000000110\n"
        )

    def _usuario(self, documento, tipo, nombres, apellidos, email, genero, telefono):
        usuario, creado = Usuario.objects.get_or_create(
            numero_documento=documento,
            defaults={"tipo_documento": tipo, "nombres": nombres, "apellidos": apellidos,
                      "email": email, "genero": genero, "telefono": telefono},
        )
        if creado:
            usuario.set_password(CLAVE)
            usuario.save(update_fields=["password"])
        return usuario
