"""
Bloqueo temporal por intentos fallidos de inicio de sesión.

Regla: 5 intentos fallidos con el mismo documento dentro de 15 minutos
bloquean ese documento hasta que el intento más antiguo "salga" de la
ventana. Mientras está bloqueado no se prueba la contraseña (ni siquiera
la correcta) y los intentos bloqueados NO alargan el castigo, así el
tiempo de espera es predecible.

Por qué por documento y no por IP: detrás del proxy del hosting todas
las personas pueden llegar con la misma IP, y bloquearla dejaría fuera
a todo el mundo. El costo de esta decisión: alguien podría bloquear a
propósito a otra persona por 15 minutos; la ventana corta lo hace
tolerable, y el administrador puede ver los intentos en el admin.
"""

import math
from datetime import timedelta

from django.utils import timezone

from core.services.auditoria import registrar as auditar
from usuarios.models import IntentoFallido

MAX_INTENTOS = 5
VENTANA_MINUTOS = 15
CONSERVAR_DIAS = 1


def normalizar(numero_documento):
    return (numero_documento or "").strip()[:20]


def minutos_de_bloqueo(numero_documento):
    """0 si puede intentar; si no, minutos (redondeados hacia arriba) que faltan."""
    documento = normalizar(numero_documento)
    if not documento:
        return 0

    ahora = timezone.now()
    desde = ahora - timedelta(minutes=VENTANA_MINUTOS)
    fechas = list(
        IntentoFallido.objects.filter(numero_documento=documento, fecha__gte=desde)
        .order_by("fecha").values_list("fecha", flat=True)
    )

    if len(fechas) < MAX_INTENTOS:
        return 0

    # El bloqueo termina cuando el fallo que lo provocó sale de la ventana.
    termina = fechas[len(fechas) - MAX_INTENTOS] + timedelta(minutes=VENTANA_MINUTOS)
    segundos = (termina - ahora).total_seconds()
    return max(1, math.ceil(segundos / 60)) if segundos > 0 else 0


def registrar_fallo(numero_documento, ip=None):
    documento = normalizar(numero_documento)
    if not documento:
        return
    IntentoFallido.objects.create(numero_documento=documento, ip=ip or None)
    if IntentoFallido.objects.filter(
        numero_documento=documento, fecha__gte=timezone.now() - timedelta(minutes=VENTANA_MINUTOS)
    ).count() == MAX_INTENTOS:
        auditar(
            "login_bloqueado",
            f"El documento {documento} se bloqueó {VENTANA_MINUTOS} minutos por {MAX_INTENTOS} intentos fallidos.",
            detalles={"documento": documento, "ip": ip},
        )
    # Limpieza barata: la tabla no crece sin límite.
    IntentoFallido.objects.filter(
        fecha__lt=timezone.now() - timedelta(days=CONSERVAR_DIAS)
    ).delete()


def limpiar(numero_documento):
    """Tras un inicio de sesión correcto se borra el historial de fallos."""
    IntentoFallido.objects.filter(numero_documento=normalizar(numero_documento)).delete()


def ip_del_cliente(request):
    """Solo informativa (no se usa para bloquear, así que un encabezado falso no ayuda a nadie)."""
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return reenviada or request.META.get("REMOTE_ADDR") or None
