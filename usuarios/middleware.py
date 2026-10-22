"""
Cierra la sesión si la persona deja de usar la aplicación un rato.

Por qué: en las salas de sistemas del SENA los computadores se comparten;
alguien que olvida cerrar sesión deja su perfil (y, si es de Bienestar, el
panel de gestión) abierto para el siguiente.

Tiempos (se pueden cambiar en settings.py):
  INACTIVIDAD_SEGUNDOS            aprendices          (por defecto 30 minutos)
  INACTIVIDAD_PERSONAL_SEGUNDOS   Bienestar y admin   (por defecto 2 horas: en un
                                  evento el escáner de QR puede pasar ratos sin
                                  peticiones y no debe sacar a quien escanea)

Para no escribir la sesión en la base de datos en CADA clic, la marca de
"última actividad" solo se actualiza si pasó al menos un minuto.
"""

import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

CLAVE_ACTIVIDAD = "_ultima_actividad"
CLAVE_LIMITE = "_limite_inactividad"
REFRESCO_SEGUNDOS = 60


class CierreSesionPorInactividadMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def _limite(self, request):
        """Límite según el rol; se calcula una vez por sesión y se guarda en ella."""
        limite = request.session.get(CLAVE_LIMITE)
        if limite is None:
            if hasattr(request.user, "aprendiz"):
                limite = getattr(settings, "INACTIVIDAD_SEGUNDOS", 30 * 60)
            else:
                limite = getattr(settings, "INACTIVIDAD_PERSONAL_SEGUNDOS", 2 * 60 * 60)
            request.session[CLAVE_LIMITE] = limite
        return limite

    def __call__(self, request):
        if request.user.is_authenticated:
            ahora = int(time.time())
            ultima = request.session.get(CLAVE_ACTIVIDAD)
            # Se calcula ya en la PRIMERA petición, junto con la marca de
            # actividad, para que la sesión se escriba una sola vez y no
            # otra más en la segunda petición.
            limite = self._limite(request)

            if ultima is not None and ahora - ultima > limite:
                logout(request)
                messages.warning(
                    request, "Tu sesión se cerró por inactividad. Inicia sesión de nuevo para continuar."
                )
                return redirect(settings.LOGIN_URL)

            if ultima is None or ahora - ultima >= REFRESCO_SEGUNDOS:
                request.session[CLAVE_ACTIVIDAD] = ahora

        return self.get_response(request)
