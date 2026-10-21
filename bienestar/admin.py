from django.contrib import admin

from bienestar.models import HorasBienestar, Asesoria, MiembroBienestar, ConfiguracionBienestar, ConstanciaHoras


@admin.register(HorasBienestar)
class HorasBienestarAdmin(admin.ModelAdmin):
    list_display = ("id", "asistencia", "cantidad_horas", "asignado_por", "fecha")


@admin.register(Asesoria)
class AsesoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "aprendiz", "personal_bienestar", "estado", "fecha_solicitud")


@admin.register(MiembroBienestar)
class MiembroBienestarAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "cargo", "correo_asesorias", "estado")


@admin.register(ConfiguracionBienestar)
class ConfiguracionBienestarAdmin(admin.ModelAdmin):
    list_display = ("id", "meta_horas", "fecha_actualizacion")


@admin.register(ConstanciaHoras)
class ConstanciaHorasAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "total_horas", "fecha_emision")
    search_fields = ("codigo", "nombre", "numero_documento")
    readonly_fields = ("codigo",)
