# -*- encoding: utf-8 -*-
"""
Management command: setup_groups

Creates the default ATENEA role groups if they don't already exist.
Idempotent — safe to run multiple times.

Usage:
    python manage.py setup_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from apps.home.decorators import ROLES


class Command(BaseCommand):
    help = "Crea los grupos de roles por defecto para ATENEA (Administrador, Investigador, Evaluador)"

    def handle(self, *args, **options):
        created_count = 0
        for role_name in ROLES:
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✔ Grupo creado: {role_name}"))
            else:
                self.stdout.write(f"  – Grupo ya existe: {role_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nListo. {created_count} grupo(s) nuevo(s) creado(s)."
            )
        )
