from django.db import models
from django.db.models import Q
from django.utils import timezone

ESTADO_CHOICES = [
    ("activa", "Activo"),
    ("cerrada", "Cerrado"),
    ("archivada", "Archivado"),
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

    def _sin_archivados(self):
        return self.exclude(estado="archivada")

    def vigentes(self, hoy=None):
        return self._sin_archivados().filter(vigente_q(hoy=hoy))

    def historial(self, hoy=None):
        """Los que ya no están vigentes: terminaron por fecha o se cerraron a mano."""
        return self._sin_archivados().exclude(vigente_q(hoy=hoy))

    def archivados(self):
        """Grupos archivados: sacados del panel principal, cuentas desactivadas."""
        return self.filter(estado="archivada")

    def con_vigencia(self, codigo, hoy=None):
        """Filtra por «vigente», «finalizado» (terminó por fecha), «cerrado» o «archivado»."""
        hoy = hoy or timezone.localdate()
        if codigo == "vigente":
            return self.vigentes(hoy)
        if codigo == "finalizado":
            return self.filter(estado="activa", fecha_fin__lt=hoy)
        if codigo == "cerrado":
            return self.filter(estado="cerrada")
        if codigo == "archivado":
            return self.archivados()
        return self


VIGENCIA_ETIQUETAS = {
    "vigente": "Vigente", "finalizado": "Finalizado",
    "cerrado": "Cerrado", "archivado": "Archivado",
}


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
        """'vigente', 'finalizado', 'cerrado' o 'archivado'."""
        if self.estado == "archivada":
            return "archivado"
        if self.estado == "cerrada":
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
