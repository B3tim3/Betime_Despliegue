"""
Configuración de Django para Be Time.

Todo lo sensible o que cambia entre entornos (local, Render, Aiven) se lee de
variables de entorno. En local se cargan desde el archivo .env; en Render se
definen en el panel Environment.
"""

import os
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# En Render el archivo .env no existe y load_dotenv simplemente no hace nada.
load_dotenv(BASE_DIR / ".env")


def env_list(nombre, default=""):
    """Convierte 'a,b,c' en ['a', 'b', 'c']."""
    return [x.strip() for x in os.getenv(nombre, default).split(",") if x.strip()]


# ---------------------------------------------------------------------------
# Seguridad básica
# ---------------------------------------------------------------------------

# Sin valor por defecto: si falta, el proyecto no arranca (mejor que fallar callado).
SECRET_KEY = os.environ["SECRET_KEY"]

# Por defecto False (seguro). Solo es True si el .env lo dice explícitamente.
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")


# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_tables2',
    'django_filters',
    # Apps propias
    'core',
    'usuarios',
    'eventos',
    'bienestar',
    'publicaciones',
    'notificaciones',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # 'whitenoise.middleware.WhiteNoiseMiddleware',  # descomentar al instalar WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'core.middleware.NoCacheParaAutenticadosMiddleware',  # descomentar si existe en tu proyecto
]

ROOT_URLCONF = 'betime.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'betime.wsgi.application'


# ---------------------------------------------------------------------------
# Base de datos (una sola variable: DATABASE_URL)
# Local:  postgres://postgres:CLAVE@localhost:5432/betime
# Aiven:  postgres://avnadmin:CLAVE@host:puerto/defaultdb?sslmode=require
# ---------------------------------------------------------------------------

DATABASES = {
    'default': dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# ---------------------------------------------------------------------------
# Contraseñas
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Archivos estáticos y subidos
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"   # destino de collectstatic en Render

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / "media"

# django-tables2: estilo Bootstrap 5 por defecto
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "usuarios.Usuario"
LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "usuarios:dashboard"
LOGOUT_REDIRECT_URL = "index"

MESSAGE_TAGS = {
    message_constants.ERROR: "danger",
}


# ---------------------------------------------------------------------------
# Correo (credenciales fuera del código)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Be Time <betimesena@gmail.com>")


# ---------------------------------------------------------------------------
# Endurecimiento: solo cuando DEBUG=False (producción)
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Render va tras un proxy