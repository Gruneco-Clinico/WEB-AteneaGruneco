# -*- encoding: utf-8 -*-
"""
Management command: asignar_codigos_pacientes

For each Proyecto that has a codigo_siu (prefix), ensures every patient
linked via the M2M has a ProyectoPacienteExtra record with a consecutive
code like  {PREFIX}_{NNNN}.

Ordering for new codes: patient ID ascending (creation order).
Existing ProyectoPacienteExtra records are respected — their codes are
NOT overwritten. Only missing records are created.

Usage:
    python manage.py asignar_codigos_pacientes          # dry-run
    python manage.py asignar_codigos_pacientes --apply   # write to DB
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.home.models import Proyecto, ProyectoPacienteExtra


class Command(BaseCommand):
    help = "Assign consecutive codes to patients per project (using codigo_siu as prefix)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Actually write to the database (default is dry-run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        total_created = 0

        for proyecto in Proyecto.objects.all().order_by("id"):
            prefix = (proyecto.codigo_siu or "").strip().upper()
            if not prefix:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP  {proyecto.nombre} — sin codigo_siu"
                    )
                )
                continue

            self.stdout.write(
                self.style.HTTP_INFO(
                    f"\n=== {proyecto.nombre}  (prefix={prefix}) ==="
                )
            )

            # ---- determine next consecutive number ----
            existing_codes = list(
                ProyectoPacienteExtra.objects.filter(proyecto=proyecto)
                .values_list("codigo_proyecto", flat=True)
            )
            max_num = 0
            pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$", re.IGNORECASE)
            for code in existing_codes:
                m = pattern.match(code)
                if m:
                    max_num = max(max_num, int(m.group(1)))

            self.stdout.write(f"  Existing codes: {len(existing_codes)}  (max={max_num})")

            # ---- find patients without PPE for this project ----
            patients_in_project = proyecto.pacientes.all().order_by("id")
            patients_with_ppe = set(
                ProyectoPacienteExtra.objects.filter(proyecto=proyecto)
                .values_list("paciente_id", flat=True)
            )

            to_create = []
            next_num = max_num + 1
            for pac in patients_in_project:
                if pac.id in patients_with_ppe:
                    continue
                code = f"{prefix}_{next_num:04d}"
                to_create.append(
                    ProyectoPacienteExtra(
                        proyecto=proyecto,
                        paciente=pac,
                        codigo_proyecto=code,
                    )
                )
                self.stdout.write(
                    f"  + {code}  →  {pac.primer_nombre} {pac.primer_apellido} (ID={pac.id})"
                )
                next_num += 1

            if not to_create:
                self.stdout.write(self.style.SUCCESS("  All patients already have codes."))
                continue

            if apply:
                with transaction.atomic():
                    ProyectoPacienteExtra.objects.bulk_create(to_create)
                self.stdout.write(
                    self.style.SUCCESS(f"  CREATED {len(to_create)} codes.")
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        f"  DRY-RUN: would create {len(to_create)} codes. Use --apply to write."
                    )
                )

            total_created += len(to_create)

        self.stdout.write(
            self.style.SUCCESS(f"\nTotal: {total_created} codes {'created' if apply else 'pending (dry-run)'}.")
        )
