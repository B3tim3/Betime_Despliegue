from django.db import models
from django.db.models import Q
from django.utils import timezone

ESTADO_CHOICES = [
    ("activa", "Activo"),
    ("cerrada", "Cerrado"),
]


def vigente_q(prefijo="", hoy=None):
    """
    Condición «grupo vigente» para usar dentro de un filter(). Con `prefijo` sirve para
    consultar a través de una relación, p. ej. vigente_q("grupos__") desde Jornada.

    Un grupo está VIGENTE si Bienestar no lo cerró a mano (estado «activa») y su fecha de fin
    todavía no pasó. Así los grupos que terminan dejan de ofrecerse solos, sin que nadie
    tenga que acordarse de cerrarlos.
    """
    hoy = hoy or timezone.localdate()
    return Q(**{f"{prefijo}estado": "activa", f"{prefijo}fecha_fin__gte": hoy})


class GrupoQuerySet(models.QuerySet):

    def vigentes(self, hoy=None):
        return self.filter(vigente_q(hoy=hoy))

    def historial(self, hoy=None):
        """Los que ya no están vigentes: terminaron por fecha o se cerraron a mano."""
        return self.exclude(vigente_q(hoy=hoy))

    def con_vigencia(self, codigo, hoy=None):
        """Filtra por «vigente», «finalizado» (terminó por fecha) o «cerrado» (a mano)."""
        hoy = hoy or timezone.localdate()
        if codigo == "vigente":
            return self.vigentes(hoy)
        if codigo == "finalizado":
            return self.filter(estado="activa", fecha_fin__lt=hoy)
        if codigo == "cerrado":
            return self.filter(estado="cerrada")
        return self


VIGENCIA_ETIQUETAS = {"vigente": "Vigente", "finalizado": "Finalizado", "cerrado": "Cerrado"}


class Grupo(models.Model):

    id = models.BigAutoField(primary_key=True)

    # ---------- Relaciones ----------

    programa_formacion = models.ForeignKey(
        "usuarios.ProgramaFormacion",
        on_delete=models.PROTECT,
        related_name="grupos"
    )

    # ---------- Información general ----------

    numero_grupo = models.CharField(
        "número de grupo",
        max_length=20,
        unique=True
    )

    jornada = models.ForeignKey(
        "usuarios.Jornada",
        on_delete=models.PROTECT,
        related_name="grupos"
    )

    # ---------- Fechas ----------

    fecha_inicio = models.DateField()

    fecha_fin = models.DateField()

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="activa"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    objects = GrupoQuerySet.as_manager()

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"

    @property
    def vigencia(self):
        """'vigente', 'finalizado' (pasó su fecha de fin) o 'cerrado' (cerrado a mano)."""
        if self.estado != "activa":
            return "cerrado"
        return "vigente" if self.fecha_fin >= timezone.localdate() else "finalizado"

    @property
    def vigencia_etiqueta(self):
        return VIGENCIA_ETIQUETAS[self.vigencia]

    @property
    def esta_vigente(self):
        return self.vigencia == "vigente"

    def __str__(self):
        return self.numero_grupo
