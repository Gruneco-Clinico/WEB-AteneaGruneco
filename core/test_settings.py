# -*- encoding: utf-8 -*-
"""
Settings de tests: usa SQLite en memoria para evitar la dependencia de
``mysqlclient`` y acelerar la ejecución. Importar con::

    DJANGO_SETTINGS_MODULE=core.test_settings python manage.py test apps.home.tests
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")

from .settings import *  # noqa: E402,F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DEBUG = False
TEMPLATE_DEBUG = False

# Desactivar middleware de rate limit para evitar interferencias en tests
MIDDLEWARE = [m for m in MIDDLEWARE if "RateLimitMiddleware" not in m]  # noqa: F405
