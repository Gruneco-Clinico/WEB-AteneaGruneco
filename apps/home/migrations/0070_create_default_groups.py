# -*- encoding: utf-8 -*-
"""
Data migration: create default role groups.

Groups: Administrador, Investigador, Evaluador.
Idempotent — uses get_or_create.
"""

from django.db import migrations


GROUPS = ["Administrador", "Investigador", "Evaluador"]


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def remove_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0069_add_proyecto_auto_visit_fields"),
    ]

    operations = [
        migrations.RunPython(create_groups, reverse_code=remove_groups),
    ]
