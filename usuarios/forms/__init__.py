from .login import LoginForm
from .registro import RegistroAprendizForm
from .crear_usuario import CrearUsuarioAdminForm
from .recuperacion import RecuperarContrasenaForm, NuevaContrasenaForm
from .catalogos import ProgramaFormacionForm, NivelFormacionForm, JornadaForm, GrupoForm, AprendizEstadoForm

__all__ = [
    "LoginForm",
    "RegistroAprendizForm",
    "CrearUsuarioAdminForm",
    "RecuperarContrasenaForm",
    "NuevaContrasenaForm",
    "ProgramaFormacionForm",
    "NivelFormacionForm",
    "JornadaForm",
    "GrupoForm",
    "AprendizEstadoForm",
]
