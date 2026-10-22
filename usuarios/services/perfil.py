from django.db import transaction


@transaction.atomic
def actualizar_perfil_aprendiz(aprendiz, datos):
    """
    Guarda los cambios de "Mi perfil" del aprendiz.

    `datos` es el cleaned_data de PerfilAprendizForm. Solo toca los datos de
    contacto y de identificación personal: nombres, apellidos, género,
    teléfono y correo. Nunca el documento, el grupo, el estado ni los
    permisos (el grupo lo cambia solo el personal de Bienestar).
    """
    usuario = aprendiz.usuario
    usuario.nombres = datos["nombres"]
    usuario.apellidos = datos["apellidos"]
    usuario.genero = datos["genero"]
    usuario.telefono = datos["telefono"]
    usuario.email = datos["email"]
    usuario.save(update_fields=["nombres", "apellidos", "genero", "telefono", "email"])
