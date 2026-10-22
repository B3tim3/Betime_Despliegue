from django.contrib import admin

from usuarios.models import (
    ProgramaFormacion,
    Jornada,
    Grupo,
    NivelFormacion,
    Usuario,
    Aprendiz,
    PersonalBienestar,
    Administrador,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "nombres", "apellidos", "tipo_documento", "numero_documento", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    search_fields = ("numero_documento", "nombres", "apellidos", "email")


@admin.register(ProgramaFormacion)
class ProgramaFormacionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "codigo", "nivel_formacion", "estado")


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ("id", "numero_grupo", "programa_formacion", "jornada", "estado")


@admin.register(Aprendiz)
class AprendizAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "grupo", "estado")


@admin.register(PersonalBienestar)
class PersonalBienestarAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "cargo", "estado")


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario")


@admin.register(NivelFormacion)
class NivelFormacionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
