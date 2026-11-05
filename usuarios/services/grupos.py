"""
Búsqueda de grupos para el registro por número de grupo.

El aprendiz escribe su número de ficha y el sistema muestra a qué programa y jornada
corresponde. Los números se comparan sin espacios y solo se aceptan grupos VIGENTES.
"""

from django.db.models import Q

from usuarios.models import Grupo


class GrupoNoDisponible(Exception):
    """El número no existe o el grupo ya no recibe registros. El mensaje es para el aprendiz."""


def normalizar_numero(texto):
    return "".join((texto or "").split())


def buscar_grupo_vigente(texto):
    numero = normalizar_numero(texto)
    if not numero:
        raise GrupoNoDisponible("Escribe el número de tu grupo.")

    grupo = (
        Grupo.objects.select_related("programa_formacion__nivel_formacion", "jornada")
        .filter(numero_grupo__iexact=numero)
        .first()
    )
    if grupo is None:
        raise GrupoNoDisponible(
            "No encontramos ese número de grupo. Revisa que esté bien escrito; si es correcto, "
            "pídele a Bienestar que lo registre."
        )
    if not grupo.esta_vigente:
        raise GrupoNoDisponible(
            "Ese grupo ya terminó y no recibe registros nuevos. Si crees que es un error, "
            "habla con Bienestar."
        )
    if grupo.programa_formacion.estado != "activo":
        raise GrupoNoDisponible("El programa de ese grupo no está disponible. Habla con Bienestar.")
    return grupo


def filtrar_grupos(params, programa_id=None, jornada_id=None):
    """
    Grupos del panel (y de su exportación) según los filtros de la URL:
      vista=vigentes (por defecto) | historial   q=texto   anio=AAAA (solo historial)
      estado=finalizado | cerrado (solo historial)
    Devuelve (queryset, vista). La lista y la exportación usan esta misma función para
    que el archivo traiga exactamente lo que se ve en pantalla.
    """
    grupos = Grupo.objects.select_related("programa_formacion", "jornada")
    if programa_id:
        grupos = grupos.filter(programa_formacion_id=programa_id)
    if jornada_id:
        grupos = grupos.filter(jornada_id=jornada_id)

    vista = "historial" if params.get("vista") == "historial" else "vigentes"

    q = (params.get("q") or "").strip()
    if q:
        grupos = grupos.filter(
            Q(numero_grupo__icontains=q)
            | Q(programa_formacion__nombre__icontains=q)
            | Q(jornada__nombre__icontains=q)
        )

    if vista == "vigentes":
        return grupos.vigentes().order_by("numero_grupo"), vista

    grupos = grupos.historial()
    anio = (params.get("anio") or "").strip()
    if anio.isdigit():
        grupos = grupos.filter(fecha_fin__year=int(anio))
    estado = params.get("estado")
    if estado in ("finalizado", "cerrado"):
        grupos = grupos.con_vigencia(estado)
    return grupos.order_by("-fecha_fin", "numero_grupo"), vista
