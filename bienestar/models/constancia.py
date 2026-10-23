import secrets

from django.db import models

# Sin 0/O ni 1/I/L: el código se escribe a mano y no debe confundirse.
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generar_codigo():
    """Código legible tipo BT-7K2M-9XQ4 (no se puede adivinar: ~10^11 combinaciones)."""
    parte = lambda: "".join(secrets.choice(_ALFABETO) for _ in range(4))
    return f"BT-{parte()}-{parte()}"


class ConstanciaHoras(models.Model):
    """
    Registro de cada constancia de horas de bienestar emitida.

    Sirve para VERIFICAR su autenticidad: el PDF lleva un código y un QR
    que apuntan a una página pública que lee este registro. Por eso se
    guarda una "foto" (nombre, documento, programa, grupo, horas) tal como
    se certificó ese día: aunque después cambie el grupo o sumen horas, la
    constancia vieja sigue diciendo exactamente lo que dijo.
    """

    id = models.BigAutoField(primary_key=True)

    codigo = models.CharField(max_length=14, unique=True, default=generar_codigo, editable=False)

    aprendiz = models.ForeignKey(
        "usuarios.Aprendiz",
        on_delete=models.CASCADE,
        related_name="constancias",
    )

    # ---------- Foto de lo certificado ----------
    nombre = models.CharField(max_length=200)
    tipo_documento = models.CharField(max_length=10)
    numero_documento = models.CharField(max_length=20)
    programa = models.CharField(max_length=200)
    grupo = models.CharField(max_length=20)
    total_horas = models.PositiveIntegerField()
    meta_horas = models.PositiveIntegerField()

    fecha_emision = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Constancia de horas"
        verbose_name_plural = "Constancias de horas"
        ordering = ["-fecha_emision"]

    @property
    def documento_oculto(self):
        """Documento parcialmente oculto para la página pública: ••••5678."""
        numero = self.numero_documento
        return "•" * max(0, len(numero) - 4) + numero[-4:]

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.total_horas} h)"
