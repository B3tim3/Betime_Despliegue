"""
Periodos de los paneles: un periodo = un AÑO calendario (sin configuración).

Para qué sirve: los paneles (eventos, publicaciones, actividades) muestran por defecto
SOLO el año vigente, así la consulta trabaja sobre unos cientos de filas aunque la tabla
acumule años de historia. Cuando llega el 1 de enero el año nuevo aparece solo, por la
fecha: no hay nada que crear ni mantener. Quien necesite lo viejo lo elige en el selector.
"""

from dataclasses import dataclass
from datetime import date, datetime

from django.db.models import Min
from django.utils import timezone



@dataclass(frozen=True)
class Periodo:
    clave: str           # "vigente" | "todos" | "2026"
    etiqueta: str
    desde: date | None   # inicio (incluido)
    hasta: date | None   # fin (EXCLUIDO); None = sin tope (vigente incluye lo futuro)

    @property
    def es_todos(self):
        return self.clave == "todos"


def anio_actual(ahora=None):
    return (timezone.localdate(ahora) if ahora else timezone.localdate()).year


def limites(anio):
    """(1 de enero, 1 de enero del año siguiente) como fechas."""
    return date(anio, 1, 1), date(anio + 1, 1, 1)


def resolver(valor, ahora=None):
    """Convierte el texto del selector (?periodo=...) en un Periodo. Lo inválido = vigente."""
    valor = (valor or "").strip()

    if valor == "todos":
        return Periodo("todos", "Todos los años", None, None)

    if valor.isdigit() and len(valor) == 4 and 2000 <= int(valor) <= 2100:
        a = int(valor)
        desde, hasta = limites(a)
        return Periodo(str(a), str(a), desde, hasta)

    anio = anio_actual(ahora)
    return Periodo("vigente", f"Año {anio}", limites(anio)[0], None)


def opciones(queryset=None, campo=None, ahora=None):
    """
    [(clave, etiqueta)] para el selector. Los años anteriores salen SOLO si hay registros:
    desde el año del registro más antiguo hasta el año pasado (un MIN sobre el campo, que
    usa el índice). Sin historial queda solo ["vigente", "todos"] y la plantilla oculta el selector.
    """
    actual = anio_actual(ahora)
    lista = [("vigente", f"Año vigente ({actual} y lo que viene)")]
    if queryset is not None and campo:
        primero = queryset.aggregate(m=Min(campo))["m"]
        if primero is not None:
            if isinstance(primero, datetime):
                primero = timezone.localtime(primero)
            for a in range(actual - 1, primero.year - 1, -1):
                lista.append((str(a), str(a)))
    lista.append(("todos", "Todos los años"))
    return lista


def filtrar(queryset, campo, periodo, como_fecha=False):
    """
    Aplica el periodo a un queryset por el campo indicado. `como_fecha=True` si el campo
    es DateField; si es DateTimeField (lo normal) se compara con el inicio del día en la
    zona horaria del proyecto.
    """
    if periodo.es_todos:
        return queryset

    def convertir(d):
        if d is None or como_fecha:
            return d
        return timezone.make_aware(datetime.combine(d, datetime.min.time()))

    if periodo.desde:
        queryset = queryset.filter(**{f"{campo}__gte": convertir(periodo.desde)})
    if periodo.hasta:
        queryset = queryset.filter(**{f"{campo}__lt": convertir(periodo.hasta)})
    return queryset


class PeriodoListMixin:
    """
    Para ListView de los paneles. La vista define `campo_periodo` (p. ej. "fecha_inicio").
    Agrega al contexto: periodo, opciones_periodo y export_extra_params (para que el
    archivo exportado traiga lo mismo que se ve), y aplica el filtro al queryset.
    """
    campo_periodo = None
    periodo_como_fecha = False

    def get_periodo(self):
        return resolver(self.request.GET.get("periodo"))

    def get_queryset(self):
        qs = super().get_queryset()
        return filtrar(qs, self.campo_periodo, self.get_periodo(), self.periodo_como_fecha)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        periodo = self.get_periodo()
        contexto["periodo"] = periodo
        contexto["opciones_periodo"] = opciones(self.model._default_manager.all(), self.campo_periodo)
        contexto["periodo_param"] = periodo.clave
        contexto["export_extra_params"] = f"periodo={periodo.clave}"
        return contexto
