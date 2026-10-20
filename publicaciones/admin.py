from django.contrib import admin
from django.db import models

from core.widgets import AdminSplitDateTimeSinSegundos
from publicaciones.models import Publicacion
from usuarios.models import Usuario


@admin.register(Publicacion)
class PublicacionAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "autor", "estado", "fecha_publicacion")
    formfield_overrides = {
        models.DateTimeField: {"widget": AdminSplitDateTimeSinSegundos},
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Una publicación la escribe Bienestar o un administrador, nunca un aprendiz.
        if db_field.name == "autor":
            kwargs["queryset"] = Usuario.objects.exclude(
                aprendiz__isnull=False
            ).order_by("apellidos", "nombres")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
