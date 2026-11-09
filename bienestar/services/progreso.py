from django.db.models import Sum

from bienestar.models import ConfiguracionBienestar, HorasBienestar


def horas_de(aprendiz):
    """
    Registros de horas que SÍ cuentan para un aprendiz: los de actividades en
    los que su asistencia está marcada como "asistió" y los de actividades
    extracurriculares cuyas horas están "otorgadas".

    Es la única fuente de verdad para el total de horas: la usan el panel,
    el historial y la constancia en PDF. Así, si Bienestar corrige una
    asistencia (desmarca "asistió") esas horas dejan de contar en todos
    lados a la vez, sin borrar el registro histórico.
    """
    # Dos consultas simples (cada una usa sus índices) unidas con UNION. Es MUCHO más
    # rápido que un solo OR sobre dos cadenas de JOIN: con 115 mil registros de horas,
    # el OR tardaba ~290 ms por visita al panel del aprendiz y esto ~17 ms.
    de_actividades = HorasBienestar.objects.filter(
        asistencia__inscripcion__aprendiz=aprendiz,
        asistencia__asistio=True,
    ).values("pk")
    extracurriculares = HorasBienestar.objects.filter(
        participacion__aprendiz=aprendiz,
        participacion__estado="otorgada",
    ).values("pk")
    return HorasBienestar.objects.filter(pk__in=de_actividades.union(extracurriculares))


def total_horas_de(aprendiz):
    return horas_de(aprendiz).aggregate(total=Sum("cantidad_horas"))["total"] or 0


def calcular_progreso(total_horas, meta=None):
    """
    Progreso de un aprendiz hacia la meta de horas de bienestar.

    Devuelve un diccionario listo para la plantilla:
      total       horas acumuladas
      meta        meta vigente (la configurada por el administrador)
      porcentaje  entero de 0 a 100 (la barra nunca pasa de 100)
      faltantes   horas que faltan (0 si ya la cumplió)
      completo    True si total >= meta
    """
    if meta is None:
        meta = ConfiguracionBienestar.obtener().meta_horas
    total = int(total_horas or 0)
    porcentaje = min(100, int(total * 100 / meta)) if meta > 0 else 100
    return {
        "total": total,
        "meta": meta,
        "porcentaje": porcentaje,
        "faltantes": max(0, meta - total),
        "completo": total >= meta,
    }
