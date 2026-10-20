from django.contrib import admin

from bienestar.models import HorasBienestar, Asesoria, MiembroBienestar


@admin.register(HorasBienestar)
class HorasBienestarAdmin(admin.ModelAdmin):
    list_display = ("id", "asistencia", "cantidad_horas", "asignado_por", "fecha")


@admin.register(Asesoria)
class AsesoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "aprendiz", "personal_bienestar", "estado", "fecha_solicitud")


@admin.register(MiembroBienestar)
class MiembroBienestarAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "cargo", "categoria", "correo_asesorias", "estado")
    list_filter = ("categoria", "estado")
