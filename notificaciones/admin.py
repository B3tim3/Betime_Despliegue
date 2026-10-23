from django.contrib import admin

from notificaciones.models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "titulo", "tipo", "leida", "fecha_creacion")
    list_filter = ("tipo", "leida")
    search_fields = ("titulo", "usuario__nombres", "usuario__apellidos", "usuario__numero_documento")
