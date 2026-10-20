from django.contrib import admin
from django.db import models

from core.widgets import AdminSplitDateTimeSinSegundos
from eventos.models import Evento, Inscripcion, Asistencia
from usuarios.models import Usuario


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "lugar", "fecha_inicio", "fecha_fin", "horas_otorgadas", "estado")
    formfield_overrides = {
        models.DateTimeField: {"widget": AdminSplitDateTimeSinSegundos},
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Un evento lo crea Bienestar o un administrador, nunca un aprendiz.
        if db_field.name == "creado_por":
            kwargs["queryset"] = Usuario.objects.exclude(
                aprendiz__isnull=False
            ).order_by("apellidos", "nombres")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ("id", "evento", "aprendiz", "estado", "fecha_inscripcion")


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ("id", "inscripcion", "asistio", "fecha_registro")
