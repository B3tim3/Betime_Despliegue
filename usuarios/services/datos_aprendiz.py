"""
Una sola definición de "qué datos de un aprendiz piden los listados de
Bienestar" (nombre, documento, género, grupo, programa, jornada, nivel,
correo y teléfono).

La usan la pantalla del checklist de asistencia y las exportaciones a
Excel / Word / PDF. Si mañana hay que agregar o quitar un dato, se cambia
SOLO aquí y todos los listados quedan iguales entre sí.

Uso:

    aprendices = Aprendiz.objects.select_related(*SELECT_RELATED_APRENDIZ)
    datos = DatosAprendiz.de(aprendiz)
    datos.como_fila()              # lista en el mismo orden de ENCABEZADOS
    DatosAprendiz.ENCABEZADOS      # títulos de las columnas
"""

from dataclasses import dataclass

# Relaciones que hay que traer de una vez para no hacer una consulta
# extra por cada aprendiz al armar un listado largo.
SELECT_RELATED_APRENDIZ = (
    "usuario",
    "grupo__jornada",
    "grupo__programa_formacion__nivel_formacion",
)


@dataclass(frozen=True)
class DatosAprendiz:
    nombre: str
    tipo_documento: str
    numero_documento: str
    genero: str
    grupo: str
    programa: str
    jornada: str
    nivel: str
    correo: str
    telefono: str

    ENCABEZADOS = (
        "Nombres y apellidos",
        "Tipo de documento",
        "Número de documento",
        "Género",
        "Número de grupo",
        "Programa de formación",
        "Jornada",
        "Nivel de formación",
        "Correo electrónico",
        "Teléfono",
    )

    @classmethod
    def de(cls, aprendiz):
        usuario = aprendiz.usuario
        grupo = aprendiz.grupo
        programa = grupo.programa_formacion

        return cls(
            nombre=usuario.get_full_name(),
            tipo_documento=usuario.tipo_documento,
            numero_documento=usuario.numero_documento,
            # Las cuentas anteriores a estos campos (o creadas por el
            # administrador) pueden no tenerlos: queda vacío, no falla.
            genero=usuario.get_genero_display() if usuario.genero else "",
            grupo=grupo.numero_grupo,
            programa=programa.nombre,
            jornada=grupo.jornada.nombre,
            nivel=programa.nivel_formacion.nombre,
            correo=usuario.email or "",
            telefono=usuario.telefono or "",
        )

    def como_fila(self):
        return [
            self.nombre, self.tipo_documento, self.numero_documento, self.genero,
            self.grupo, self.programa, self.jornada, self.nivel, self.correo, self.telefono,
        ]

    def texto_busqueda(self):
        """Todo el texto de la fila en minúsculas, para el filtro ?q= de las exportaciones."""
        return " ".join(self.como_fila()).lower()
