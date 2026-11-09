from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone

from core.imagenes_mixin import ImagenOptimizadaMixin

ESTADO_CHOICES = [
    ("programado", "Programada"),
    ("en_curso", "En curso"),
    ("finalizado", "Finalizada"),
    ("cancelado", "Cancelada"),
]


class ActividadQuerySet(models.QuerySet):

    def con_cupos(self):
        """
        Agrega `inscritos_n` (inscripciones NO canceladas) a cada actividad en la misma
        consulta, para que las listas muestren "12 de 30" sin una consulta por fila.
        """
        return self.annotate(
            inscritos_n=Count("inscripciones", filter=~Q(inscripciones__estado="cancelada"))
        )


class Actividad(ImagenOptimizadaMixin, models.Model):

    objects = ActividadQuerySet.as_manager()

    id = models.BigAutoField(primary_key=True)

    # ---------- Información general ----------

    titulo = models.CharField(
        max_length=150
    )

    descripcion = models.TextField(
        blank=True
    )

    lugar = models.CharField(
        max_length=150
    )

    horas_otorgadas = models.PositiveIntegerField(
        default=0
    )

    # Vacío = sin límite. Cuenta las inscripciones que no están canceladas: al cancelar
    # (o al no asistir alguien) el lugar se libera solo, no hay contador que mantener.
    cupo_maximo = models.PositiveIntegerField(
        "Cupo máximo",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Número máximo de aprendices que pueden inscribirse. Déjalo vacío si no hay límite."
    )

    imagen = models.ImageField(
        upload_to="actividades/",
        null=True,
        blank=True
    )

    # ---------- Relaciones ----------

    creado_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="actividades_creados"
    )

    # ---------- Fechas ----------

    fecha_inicio = models.DateTimeField()

    fecha_fin = models.DateTimeField()

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    # ---------- Estados ----------

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="programado"
    )

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        constraints = [
            models.CheckConstraint(
                condition=Q(cupo_maximo__isnull=True) | Q(cupo_maximo__gte=1),
                name="actividad_cupo_positivo",
            ),
        ]
        indexes = [
            # Los paneles filtran por periodo y ordenan por esta fecha en cada visita.
            models.Index(fields=["fecha_inicio"], name="actividad_fecha_inicio_idx"),
        ]

    # ---------- Estado automático ----------
    # programado / en curso / finalizado salen de las fechas; "cancelado" es el
    # único que se pone a mano y nunca se pisa (ver actividades/services/estados.py).

    @staticmethod
    def calcular_estado(fecha_inicio, fecha_fin, ahora=None):
        ahora = ahora or timezone.now()
        if ahora >= fecha_fin:
            return "finalizado"
        if ahora >= fecha_inicio:
            return "en_curso"
        return "programado"

    @property
    def estado_actual(self):
        """El estado de AHORA MISMO, sin depender de que la base de datos esté al día."""
        if self.estado == "cancelado":
            return "cancelado"
        return self.calcular_estado(self.fecha_inicio, self.fecha_fin)

    # ---------- Cupo ----------

    @property
    def inscritos_activos(self):
        """Inscripciones que ocupan lugar (todas menos las canceladas)."""
        if hasattr(self, "inscritos_n"):          # viene de con_cupos(): sin consulta extra
            return self.inscritos_n
        if self.pk is None:
            return 0
        return self.inscripciones.exclude(estado="cancelada").count()

    @property
    def tiene_cupo_limitado(self):
        return self.cupo_maximo is not None

    @property
    def cupos_disponibles(self):
        """None si no hay límite; si hay, cuántos lugares quedan (nunca negativo)."""
        if self.cupo_maximo is None:
            return None
        return max(self.cupo_maximo - self.inscritos_activos, 0)

    @property
    def esta_lleno(self):
        return self.cupo_maximo is not None and self.inscritos_activos >= self.cupo_maximo

    def save(self, *args, **kwargs):
        if self.estado != "cancelado":
            self.estado = self.calcular_estado(self.fecha_inicio, self.fecha_fin)
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = list(kwargs["update_fields"]) + ["estado"]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo
