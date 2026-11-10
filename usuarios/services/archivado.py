"""
Archivado y restauración de grupos egresados.

Archivar un grupo:
  1. Cambia su estado a «archivada».
  2. Desactiva (is_active=False) las cuentas de los aprendices que
     pertenecen SOLO a ese grupo y no tienen otra actividad vigente.
  3. Conserva todos los registros (asistencia, horas, inscripciones)
     para consulta futura.

Restaurar un grupo:
  1. Devuelve el estado a «cerrada» (no a «activa», porque ya egresó).
  2. Reactiva las cuentas que se desactivaron al archivar.

Eliminar definitivamente:
  Solo desde el panel de archivados. Elimina el grupo y sus aprendices
  con todo su historial. Irreversible.
"""

from django.db import transaction

from usuarios.models import Aprendiz, Grupo


@transaction.atomic
def archivar_grupo(grupo):
    """
    Archiva el grupo y desactiva las cuentas de sus aprendices.
    Devuelve la cantidad de cuentas desactivadas.
    """
    aprendices = Aprendiz.objects.filter(grupo=grupo).select_related("usuario")
    desactivados = 0
    for aprendiz in aprendices:
        usuario = aprendiz.usuario
        if usuario.is_active:
            usuario.is_active = False
            usuario.save(update_fields=["is_active"])
            desactivados += 1

    grupo.estado = "archivada"
    grupo.save(update_fields=["estado"])
    return desactivados


@transaction.atomic
def restaurar_grupo(grupo):
    """
    Saca el grupo del archivo (vuelve a «cerrada») y reactiva las cuentas.
    Devuelve la cantidad de cuentas reactivadas.
    """
    aprendices = Aprendiz.objects.filter(grupo=grupo).select_related("usuario")
    reactivados = 0
    for aprendiz in aprendices:
        usuario = aprendiz.usuario
        if not usuario.is_active:
            usuario.is_active = True
            usuario.save(update_fields=["is_active"])
            reactivados += 1

    grupo.estado = "cerrada"
    grupo.save(update_fields=["estado"])
    return reactivados


@transaction.atomic
def eliminar_grupo_definitivamente(grupo):
    """
    Elimina el grupo archivado, sus aprendices y las cuentas de usuario
    asociadas. Solo funciona con grupos en estado «archivada».
    Devuelve la cantidad de cuentas eliminadas.
    """
    if grupo.estado != "archivada":
        raise ValueError("Solo se pueden eliminar definitivamente grupos archivados.")

    aprendices = Aprendiz.objects.filter(grupo=grupo).select_related("usuario")
    eliminados = aprendices.count()

    # Eliminar usuarios (el CASCADE de Aprendiz.usuario borra el Aprendiz,
    # y las inscripciones/asistencias tienen CASCADE desde Aprendiz).
    for aprendiz in aprendices:
        aprendiz.usuario.delete()

    grupo.delete()
    return eliminados
