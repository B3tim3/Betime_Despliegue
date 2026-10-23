from django.contrib import admin

from core.models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Solo lectura: una bitácora no se edita ni se borra."""

    list_display = ("fecha", "accion", "usuario_texto", "descripcion")
    list_filter = ("accion",)
    search_fields = ("usuario_texto", "descripcion")
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
