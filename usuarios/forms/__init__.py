from .login import LoginForm
from .perfil import PerfilAprendizForm, CambiarContrasenaForm
from .registro import RegistroAprendizForm
from .crear_usuario import CrearUsuarioAdminForm
from .recuperacion import RecuperarContrasenaForm, NuevaContrasenaForm
from .catalogos import ProgramaFormacionForm, NivelFormacionForm, JornadaForm, GrupoForm, AprendizEstadoForm

__all__ = [
    "PerfilAprendizForm",
    "CambiarContrasenaForm",
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
