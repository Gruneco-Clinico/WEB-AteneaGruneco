import os
from decouple import config, Csv
from unipath import Path
from django.contrib.messages import constants as message_constants

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).parent
CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
# No default — forces .env to be configured before the app starts.
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

# load production server from .env
ALLOWED_HOSTS = [
    "3.85.96.200",  # Dirección IP de tu servidor de producción
    "www.gruneco.com.co",  # Nombre de dominio de tu servidor de producción
    "gruneco.com.co",  # Otro nombre de dominio de producción
    "localhost",  # Permitir el acceso desde localhost (útil para desarrollo)
    "127.0.0.1",  # Permitir el acceso desde la dirección local (útil para desarrollo)
]
CSRF_TRUSTED_ORIGINS = ["https://www.gruneco.com.co", "https://gruneco.com.co"]
# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.home",  # Enable the inner home (home)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
# Configuraciones de login
LOGIN_URL = "accounts/login"  # URL para el login
LOGIN_REDIRECT_URL = "home"  # URL después de login exitoso
LOGOUT_REDIRECT_URL = "accounts/login"  # URL después de logout

ROOT_URLCONF = "core.urls"
TEMPLATE_DIR = os.path.join(CORE_DIR, "apps/templates")  # ROOT dir for templates

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.mysql"),
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="3306"),
        "OPTIONS": {
            "unix_socket": config("DB_UNIX_SOCKET", default="/opt/bitnami/mariadb/tmp/mysql.sock"),
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "es"

TIME_ZONE = "America/Bogota"

USE_I18N = True

USE_L10N = True

USE_TZ = True

#############################################################
# SRC: https://devcenter.heroku.com/articles/django-assets

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_ROOT = os.path.join(CORE_DIR, "staticfiles")
STATIC_URL = "/static/"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (os.path.join(CORE_DIR, "apps/static"),)


#############################################################
#############################################################


MESSAGE_TAGS = {
    message_constants.DEBUG: "debug",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "error",
}

{"html.format.enable": False, "files.associations": {"*.html": "django-html"}}

#### INTEGRACIÓN RECUÉRDAME

POSTHOG_PERSONAL_API_KEY = config("POSTHOG_PERSONAL_API_KEY", default="")
POSTHOG_API_KEY = POSTHOG_PERSONAL_API_KEY  # Alias for posthog_service.py compatibility
POSTHOG_PROJECT_ID = config("POSTHOG_PROJECT_ID", default="")
POSTHOG_API_URL = config("POSTHOG_API_URL", default="https://us.posthog.com")
POSTHOG_DAU_INSIGHT_ID = config("POSTHOG_DAU_INSIGHT_ID", default="")
POSTHOG_GROWTH_INSIGHT_ID = config("POSTHOG_GROWTH_INSIGHT_ID", default="")
POSTHOG_DEVICE_TYPE_INSIGHT_ID = config("POSTHOG_DEVICE_TYPE_INSIGHT_ID", default="")
POSTHOG_IDENTIFY_COUNT_INSIGHT_ID = config("POSTHOG_IDENTIFY_COUNT_INSIGHT_ID", default="")
POSTHOG_SESION_TIME_INSIGHT_ID = config("POSTHOG_SESION_TIME_INSIGHT_ID", default="")
POSTHOG_VIEWS_PER_PAGE = config("POSTHOG_VIEWS_PER_PAGE", default="")
POSTHOG_PAGES_VIEWS_PER_USER = config("POSTHOG_PAGES_VIEWS_PER_USER", default="")
POSTHOG_DAU_PER_USER_ID = config("POSTHOG_DAU_PER_USER_ID", default="")
POSTHOG_AUTOCAPTURE_PER_USER_ID = config("POSTHOG_AUTOCAPTURE_PER_USER_ID", default="")


# Configuración del correo electrónico usando Gmail SMTP

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)

EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Atenea Gruneco <ateneagruneco@gmail.com>")


# ----- Security Hardening -----
# Only enforce HTTPS/secure cookies when NOT in DEBUG mode (production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    X_FRAME_OPTIONS = "SAMEORIGIN"
