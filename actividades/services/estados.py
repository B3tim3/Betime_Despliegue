"""
Estado automático de las actividades.

Un actividad está "programado" antes de su fecha de inicio, "en curso" entre
el inicio y el fin, y "finalizado" después del fin. Nadie lo cambia a mano:
se calcula con las fechas. La única excepción es "cancelado", que sí se
pone a mano (por eso nunca se pisa).

El estado se guarda en la base de datos (así los filtros, el panel y las
exportaciones lo siguen leyendo igual que siempre), y se mantiene al día de
dos formas:
  1) Actividad.save() lo recalcula cada vez que se crea o edita una actividad.
  2) sincronizar_estados() lo corrige en bloque con tres UPDATE; las vistas
     que muestran o usan el estado lo llaman al empezar, así que el cambio
     se ve en cuanto pasa la hora, sin esperar a que alguien edite la actividad.
"""

from django.utils import timezone

from actividades.models import Actividad


def sincronizar_estados(ahora=None):
    """
    Pone al día el estado de todos las actividades no cancelados según las
    fechas. Devuelve cuántos actividades cambiaron. Es barato: cada UPDATE
    solo toca las filas que de verdad están desactualizadas.
    """
    ahora = ahora or timezone.now()
    vivos = Actividad.objects.exclude(estado="cancelado")

    cambiados = vivos.filter(fecha_fin__lte=ahora).exclude(estado="finalizado").update(estado="finalizado")
    cambiados += vivos.filter(
        fecha_inicio__lte=ahora, fecha_fin__gt=ahora
    ).exclude(estado="en_curso").update(estado="en_curso")
    cambiados += vivos.filter(fecha_inicio__gt=ahora).exclude(estado="programado").update(estado="programado")
    return cambiados
