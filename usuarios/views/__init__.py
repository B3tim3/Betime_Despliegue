"""
Vistas de la app usuarios, divididas por tema.

Este archivo vuelve a exportar todas las vistas para que `usuarios/urls.py` y el
resto del proyecto sigan usando `from usuarios import views` / `views.nombre` sin cambios.
"""

from .autenticacion import (  # noqa: F401
    jornadas_por_programa,
    grupos_por_programa,
    registro_aprendiz,
    login_view,
    logout_view,
)
from .dashboards import (  # noqa: F401
    dashboard_redirect,
    dashboard_aprendiz,
    dashboard_bienestar,
    dashboard_admin,
)
from .cuentas import (  # noqa: F401
    crear_usuario_admin,
    perfil_aprendiz,
    CambiarContrasenaView,
)
from .catalogos import (  # noqa: F401
    EliminarProtegidoMixin,
    ProgramaFormacionListView,
    ProgramaFormacionCreateView,
    ProgramaFormacionUpdateView,
    ProgramaFormacionDeleteView,
    NivelFormacionListView,
    NivelFormacionCreateView,
    NivelFormacionUpdateView,
    NivelFormacionDeleteView,
    JornadaListView,
    JornadaCreateView,
    JornadaUpdateView,
    JornadaDeleteView,
    GrupoListView,
    GrupoCreateView,
    GrupoUpdateView,
    GrupoDeleteView,
)
from .aprendices import (  # noqa: F401
    AprendizListView,
    AprendizUpdateView,
    AprendizDeleteView,
)
from .exportaciones import (  # noqa: F401
    exportar_programas,
    exportar_niveles,
    exportar_jornadas,
    exportar_grupos,
    exportar_aprendices,
)

__all__ = [
    "jornadas_por_programa",
    "grupos_por_programa",
    "registro_aprendiz",
    "login_view",
    "logout_view",
    "dashboard_redirect",
    "dashboard_aprendiz",
    "dashboard_bienestar",
    "dashboard_admin",
    "crear_usuario_admin",
    "perfil_aprendiz",
    "CambiarContrasenaView",
    "EliminarProtegidoMixin",
    "ProgramaFormacionListView",
    "ProgramaFormacionCreateView",
    "ProgramaFormacionUpdateView",
    "ProgramaFormacionDeleteView",
    "NivelFormacionListView",
    "NivelFormacionCreateView",
    "NivelFormacionUpdateView",
    "NivelFormacionDeleteView",
    "JornadaListView",
    "JornadaCreateView",
    "JornadaUpdateView",
    "JornadaDeleteView",
    "GrupoListView",
    "GrupoCreateView",
    "GrupoUpdateView",
    "GrupoDeleteView",
    "AprendizListView",
    "AprendizUpdateView",
    "AprendizDeleteView",
    "exportar_programas",
    "exportar_niveles",
    "exportar_jornadas",
    "exportar_grupos",
    "exportar_aprendices",
]
