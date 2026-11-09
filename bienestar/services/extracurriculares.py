"""
Horas de bienestar por mérito: horas de bienestar que se dan FUERA de las actividades
(por portar bien el uniforme, prestar atención en una charla, etc.).

Reglas (iguales a las de las actividades para que se sientan parecidas):
  * Una participación = un aprendiz dentro de una actividad (único).
  * Dar horas dos veces no duplica nada: se actualiza el mismo registro.
  * Quitar las horas NO borra el registro (queda el historial); simplemente
    la participación vuelve a "pendiente" y deja de contar.
  * Todo cambio de horas queda en la bitácora y le avisa al aprendiz.
"""

from django.core import signing
from django.db import transaction

from bienestar.models import (
    ActividadExtracurricular,
    HorasBienestar,
    ParticipacionExtracurricular,
)
from core.services.auditoria import registrar as auditar
from notificaciones.services import notificar
from usuarios.models import Aprendiz

SAL_QR = "betime.extracurricular.qr"


class ExtracurricularError(Exception):
    """Algo que el usuario puede corregir; el mensaje se muestra tal cual."""


# ---------- QR personal del aprendiz ----------
# El QR NO se guarda en la base de datos: es un token firmado con la
# SECRET_KEY que dice "este es el aprendiz N". Nadie puede inventar uno para
# otra persona, y no hace falta una columna nueva en Aprendiz.

def token_qr_de(aprendiz):
    return signing.dumps({"aprendiz": aprendiz.pk}, salt=SAL_QR, compress=False)


def aprendiz_de_token(token):
    try:
        datos = signing.loads(token, salt=SAL_QR)
    except signing.BadSignature:
        return None
    return Aprendiz.objects.select_related("usuario", "grupo").filter(pk=datos.get("aprendiz")).first()


# ---------- Código ----------

def normalizar_codigo(texto):
    return "".join((texto or "").split()).upper()


@transaction.atomic
def unirse_con_codigo(aprendiz, codigo):
    """
    El aprendiz ingresa el código: queda en la lista de la actividad,
    pendiente de que Bienestar le asigne las horas. Devuelve (participacion, creada).
    """
    codigo = normalizar_codigo(codigo)
    if not codigo:
        raise ExtracurricularError("Escribe el código que te dio Bienestar.")

    actividad = ActividadExtracurricular.objects.filter(codigo=codigo).first()
    if actividad is None:
        raise ExtracurricularError("Ese código no existe. Revísalo e inténtalo de nuevo.")
    if not actividad.abierta:
        raise ExtracurricularError("Ese motivo ya está cerrado, no recibe más participantes.")

    participacion, creada = ParticipacionExtracurricular.objects.get_or_create(
        actividad=actividad, aprendiz=aprendiz, defaults={"metodo": "codigo"},
    )
    return participacion, creada


# ---------- Horas ----------

def _plural(n):
    return f"{n} hora{'s' if n != 1 else ''}"


@transaction.atomic
def otorgar_horas(*, actividad, aprendiz, horas, asignado_por, metodo, request=None):
    """
    Deja la participación del aprendiz como "otorgada" con `horas` horas.
    Devuelve (participacion, cambio) con cambio = "nueva" | "actualizada" | "igual".
    """
    if horas < 1:
        raise ExtracurricularError("Las horas deben ser al menos 1.")

    participacion, _ = ParticipacionExtracurricular.objects.get_or_create(
        actividad=actividad, aprendiz=aprendiz, defaults={"metodo": metodo},
    )
    # Bloquea la fila: dos escaneos simultáneos del mismo QR no duplican horas.
    participacion = ParticipacionExtracurricular.objects.select_for_update().get(pk=participacion.pk)

    previas = HorasBienestar.objects.filter(participacion=participacion).first()
    if participacion.estado == "otorgada" and previas is not None and previas.cantidad_horas == horas:
        return participacion, "igual"

    cambio = "actualizada" if participacion.estado == "otorgada" else "nueva"
    participacion.estado = "otorgada"
    participacion.metodo = metodo if cambio == "nueva" else participacion.metodo
    participacion.save(update_fields=["estado", "metodo"])

    HorasBienestar.objects.update_or_create(
        participacion=participacion,
        defaults={
            "cantidad_horas": horas,
            "motivo": f"Actividad por mérito: {actividad.titulo}",
            "asignado_por": asignado_por,
        },
    )

    usuario = aprendiz.usuario
    notificar(
        usuario,
        f"Se registraron {_plural(horas)} de bienestar",
        f"Por la actividad por mérito «{actividad.titulo}». Puedes verlas en tu historial.",
        url="/bienestar/mi-historial/",
        tipo="horas",
    )
    auditar(
        "asistencia",
        f"Horas de bienestar por mérito: {usuario.get_full_name()} ({usuario.numero_documento}) "
        f"en «{actividad.titulo}», {horas} horas.",
        usuario=asignado_por.usuario, request=request,
        detalles={"actividad_id": actividad.pk, "participacion_id": participacion.pk,
                  "metodo": metodo, "horas": horas, "extracurricular": True},
    )
    return participacion, cambio


@transaction.atomic
def quitar_horas(*, participacion, asignado_por, request=None):
    """Deshace una asignación: vuelve a pendiente y deja de contar (el registro queda)."""
    participacion = ParticipacionExtracurricular.objects.select_for_update().select_related(
        "actividad", "aprendiz__usuario").get(pk=participacion.pk)
    if participacion.estado != "otorgada":
        return participacion, False

    participacion.estado = "pendiente"
    participacion.save(update_fields=["estado"])

    usuario = participacion.aprendiz.usuario
    auditar(
        "asistencia",
        f"Horas de bienestar por mérito retiradas: {usuario.get_full_name()} ({usuario.numero_documento}) "
        f"en «{participacion.actividad.titulo}».",
        usuario=asignado_por.usuario, request=request,
        detalles={"actividad_id": participacion.actividad_id,
                  "participacion_id": participacion.pk, "extracurricular": True, "retiradas": True},
    )
    return participacion, True


def horas_otorgadas_de(participacion):
    registro = HorasBienestar.objects.filter(participacion=participacion).first()
    return registro.cantidad_horas if registro else None
