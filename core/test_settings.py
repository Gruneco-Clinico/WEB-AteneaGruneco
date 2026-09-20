# -*- encoding: utf-8 -*-
"""Settings mínimos para tests locales (SQLite, sin cadena de migraciones MySQL rota)."""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

ALLOWED_HOSTS = ["*", "testserver", "localhost", "127.0.0.1"]


class _DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = _DisableMigrations()
