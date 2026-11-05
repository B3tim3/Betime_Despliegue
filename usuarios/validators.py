"""
Validación del número de documento.

Por qué existe: el número de documento es el USUARIO con el que la persona inicia sesión
y la llave con la que Bienestar la identifica en listados, constancias y exportaciones. Si
alguien escribe ahí su correo, un nombre o símbolos, la cuenta queda con una identificación
inválida (y el formulario solo limitaba el largo). Esta regla se aplica al registrar, al crear
usuarios y al corregir aprendices.

Reglas (editables aquí, en un solo lugar):
  - Cédula de ciudadanía (CC), tarjeta de identidad (TI) y cédula de extranjería (CE):
    SOLO dígitos, de 5 a 12.
  - PEP y PPT (permisos para extranjeros): letras y números, sin espacios ni símbolos,
    de 5 a 20 caracteres; se guardan en MAYÚSCULAS para que "abc123" y "ABC123" sean el mismo.
"""

import re

from django.core.exceptions import ValidationError

TIPOS_ALFANUMERICOS = {"PEP", "PPT"}

LARGO_NUMERICO = (5, 12)
LARGO_ALFANUMERICO = (5, 20)

# [0-9] y no \d: \d también acepta dígitos de otros alfabetos (p. ej. árabes).
_SOLO_DIGITOS = re.compile(r"[0-9]+")
_ALFANUMERICO = re.compile(r"[A-Za-z0-9]+")


def validar_numero_documento(tipo, numero):
    """
    Devuelve el número normalizado o lanza ValidationError con un mensaje claro.

    `tipo` puede ser None (el tipo ya falló su propia validación): en ese caso solo se
    limpia el texto, porque el formulario ya es inválido de todos modos.
    """
    numero = (numero or "").strip()
    if not numero:
        raise ValidationError("Escribe el número de documento.")

    if tipo is None:
        return numero

    if tipo in TIPOS_ALFANUMERICOS:
        minimo, maximo = LARGO_ALFANUMERICO
        if not _ALFANUMERICO.fullmatch(numero):
            raise ValidationError(
                "Para este tipo de documento solo se permiten letras y números, sin espacios ni símbolos."
            )
        if not minimo <= len(numero) <= maximo:
            raise ValidationError(f"El número de documento debe tener entre {minimo} y {maximo} caracteres.")
        return numero.upper()

    minimo, maximo = LARGO_NUMERICO
    if not _SOLO_DIGITOS.fullmatch(numero):
        raise ValidationError(
            "El número de documento solo puede tener números: sin letras, espacios, puntos ni símbolos."
        )
    if not minimo <= len(numero) <= maximo:
        raise ValidationError(f"El número de documento debe tener entre {minimo} y {maximo} dígitos.")
    return numero


def documento_es_valido(tipo, numero):
    try:
        validar_numero_documento(tipo, numero)
    except ValidationError:
        return False
    return True
