# -*- encoding: utf-8 -*-
"""
Management command: seed_form_builder_demo

Seeds the minimum set of records needed to test the Form Builder end-to-end:

    - Superuser ``admin`` (password ``admin12345``) unless one already exists.
    - One ``Proyecto`` ("Demo Form Builder").
    - One ``TipoVisita`` ("Visita Inicial") linked to the Proyecto.
    - One ``DatosDemograficos`` patient linked to the Proyecto.
    - Two builder-based ``Examen`` records (text/radio/select + antropometria
      with repeater and computed IMC), each with a published
      ``ExamenSchemaVersion``.
    - A ``Visita`` for the patient with ``VisitaExamen`` entries for both
      builder exams.

The command is idempotent: running it twice will not create duplicates.

Usage:
    python manage.py seed_form_builder_demo
"""

from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.home.models import (
    DatosDemograficos,
    Examen,
    ExamenSchemaVersion,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
)


DEMO_PROJECT_NAME = "Demo Form Builder"
DEMO_TIPO_VISITA = "Visita Inicial"
DEMO_PATIENT_DOC = "1000000001"

SCHEMA_CLINICO_BASICO = [
    {
        "type": "section",
        "label": "Datos generales",
        "fields": [
            {
                "id": "motivo_consulta",
                "type": "text",
                "label": "Motivo de consulta",
                "required": True,
            },
            {
                "id": "tiempo_evolucion",
                "type": "number",
                "label": "Tiempo de evolución (meses)",
                "min": 0,
                "max": 1200,
            },
        ],
    },
    {
        "type": "section",
        "label": "Antecedentes",
        "fields": [
            {
                "id": "antecedente_familiar",
                "type": "radio",
                "label": "¿Tiene antecedentes familiares de demencia?",
                "options": [
                    {"value": "si", "label": "Sí"},
                    {"value": "no", "label": "No"},
                    {"value": "no_sabe", "label": "No sabe"},
                ],
                "required": True,
            },
            {
                "id": "parentesco",
                "type": "select",
                "label": "Parentesco principal",
                "options": [
                    {"value": "padre", "label": "Padre"},
                    {"value": "madre", "label": "Madre"},
                    {"value": "hermano", "label": "Hermano/a"},
                    {"value": "abuelo", "label": "Abuelo/a"},
                ],
                "visible_when": {"field": "antecedente_familiar", "equals": "si"},
            },
        ],
    },
    {
        "type": "section",
        "label": "Observaciones",
        "fields": [
            {
                "id": "observaciones",
                "type": "text",
                "label": "Observaciones del evaluador",
                "multiline": True,
            },
        ],
    },
]

SCHEMA_ANTROPOMETRIA = [
    {
        "type": "section",
        "label": "Medidas básicas",
        "fields": [
            {
                "id": "peso_kg",
                "type": "number",
                "label": "Peso (kg)",
                "min": 0,
                "max": 400,
                "required": True,
            },
            {
                "id": "talla_m",
                "type": "number",
                "label": "Talla (m)",
                "min": 0,
                "max": 3,
                "step": 0.01,
                "required": True,
            },
            {
                "id": "imc",
                "type": "computed",
                "label": "IMC",
                "formula": "peso_kg / (talla_m * talla_m)",
                "precision": 2,
            },
        ],
    },
    {
        "type": "section",
        "label": "Síntomas",
        "fields": [
            {
                "id": "sintomas",
                "type": "repeater",
                "label": "Síntomas reportados",
                "add_label": "Agregar síntoma",
                "fields": [
                    {
                        "id": "nombre",
                        "type": "text",
                        "label": "Síntoma",
                        "required": True,
                    },
                    {
                        "id": "severidad",
                        "type": "select",
                        "label": "Severidad",
                        "options": [
                            {"value": "leve", "label": "Leve"},
                            {"value": "moderada", "label": "Moderada"},
                            {"value": "severa", "label": "Severa"},
                        ],
                    },
                    {
                        "id": "requiere_medicacion",
                        "type": "boolean",
                        "label": "¿Requiere medicación?",
                    },
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Siembra datos mínimos (proyecto, tipo de visita, paciente, visita, "
        "exámenes del builder) para probar el módulo Form Builder."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-schemas",
            action="store_true",
            help=(
                "Borra las ExamenSchemaVersion existentes de los exámenes demo "
                "y re-publica el schema desde cero."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        admin = self._ensure_admin(User)
        self._ensure_groups()

        proyecto = self._ensure_proyecto()
        tipo_visita = self._ensure_tipo_visita(proyecto)
        paciente = self._ensure_paciente(proyecto)

        examen_clinico = self._ensure_examen(
            nombre="Demo Form Builder — Clínico básico",
            categoria="CLINICAS",
            descripcion=(
                "Examen demo con texto, número, radio condicional y select para "
                "probar el renderizado y guardado del builder."
            ),
            campos=SCHEMA_CLINICO_BASICO,
            admin=admin,
            reset=options["reset_schemas"],
        )
        examen_antropo = self._ensure_examen(
            nombre="Demo Form Builder — Antropometría",
            categoria="MEDICAS",
            descripcion=(
                "Examen demo con campo calculado (IMC) y repeater de síntomas."
            ),
            campos=SCHEMA_ANTROPOMETRIA,
            admin=admin,
            reset=options["reset_schemas"],
        )

        self._assign_examenes_to_tipo_visita(
            tipo_visita, [examen_clinico, examen_antropo]
        )

        visita = self._ensure_visita(paciente, tipo_visita, admin)
        self._ensure_visita_examenes(visita, [examen_clinico, examen_antropo])

        self._print_summary(
            admin=admin,
            proyecto=proyecto,
            tipo_visita=tipo_visita,
            paciente=paciente,
            visita=visita,
            examenes=[examen_clinico, examen_antropo],
        )

    def _ensure_admin(self, User):
        admin = User.objects.filter(is_superuser=True).first()
        if admin:
            self.stdout.write(f"  - Superusuario existente: {admin.username}")
            return admin
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin12345",
            first_name="Admin",
            last_name="Demo",
        )
        self.stdout.write(
            self.style.SUCCESS(
                "  ✔ Superusuario creado: admin / admin12345 "
                "(cámbialo después de iniciar sesión)"
            )
        )
        return admin

    def _ensure_groups(self):
        try:
            from apps.home.decorators import ROLES
        except Exception:
            return
        for role_name in ROLES:
            Group.objects.get_or_create(name=role_name)

    def _ensure_proyecto(self) -> Proyecto:
        proyecto, created = Proyecto.objects.get_or_create(
            nombre=DEMO_PROJECT_NAME,
            defaults={
                "descripcion": "Proyecto de ejemplo para probar el Form Builder.",
                "investigador_principal": "Demo",
                "codigo_siu": "FB-DEMO",
                "fecha_inicio": date.today(),
                "crear_visita_automatica": False,
            },
        )
        verbo = "Creado" if created else "Existente"
        self.stdout.write(f"  - Proyecto {verbo}: {proyecto.nombre}")
        return proyecto

    def _ensure_tipo_visita(self, proyecto: Proyecto) -> TipoVisita:
        tipo_visita, created = TipoVisita.objects.get_or_create(
            nombre=DEMO_TIPO_VISITA,
            proyecto=proyecto,
            defaults={
                "observaciones": "Tipo de visita demo para el Form Builder.",
                "examenes": [],
            },
        )
        verbo = "Creado" if created else "Existente"
        self.stdout.write(f"  - TipoVisita {verbo}: {tipo_visita.nombre}")
        return tipo_visita

    def _ensure_paciente(self, proyecto: Proyecto) -> DatosDemograficos:
        paciente = DatosDemograficos.objects.filter(
            numero_documento=DEMO_PATIENT_DOC
        ).first()
        if not paciente:
            paciente = DatosDemograficos.objects.create(
                primer_nombre="Ana",
                segundo_nombre="María",
                primer_apellido="Demo",
                segundo_apellido="Builder",
                tipo_documento="CC",
                numero_documento=DEMO_PATIENT_DOC,
                celular="3000000001",
                fecha_nacimiento=date(1980, 1, 1),
                edad=45,
                genero="F",
                municipio_nacimiento="Medellín",
                departamento_nacimiento="Antioquia",
                pais_nacimiento="Colombia",
                estado_civil="Soltero",
                escolaridad="universidad",
                ocupacion="Docente",
                lateralidad="Diestro",
                grupo_sanguineo="O+",
                religion="N/A",
                eps="N/A",
                regimen="Contributivo",
                direccion="Calle 123 #45-67",
                municipio_residencia="Medellín",
                departamento_residencia="Antioquia",
                pais_residencia="Colombia",
                correo="paciente.demo@example.com",
            )
            self.stdout.write(
                self.style.SUCCESS(f"  ✔ Paciente creado: {paciente.numero_documento}")
            )
        else:
            self.stdout.write(
                f"  - Paciente existente: {paciente.numero_documento}"
            )

        if not proyecto.pacientes.filter(id=paciente.id).exists():
            proyecto.pacientes.add(paciente)
            self.stdout.write("    ↳ Vinculado al proyecto demo.")
        return paciente

    def _ensure_examen(
        self,
        *,
        nombre: str,
        categoria: str,
        descripcion: str,
        campos: list,
        admin,
        reset: bool,
    ) -> Examen:
        examen, created = Examen.objects.get_or_create(
            nombre=nombre,
            defaults={
                "categoria": categoria,
                "descripcion": descripcion,
                "campos": campos,
            },
        )
        if not created:
            examen.categoria = categoria
            examen.descripcion = descripcion
            examen.campos = campos
            examen.save(update_fields=["categoria", "descripcion", "campos"])

        if reset:
            examen.schema_versions.all().delete()

        latest = examen.schema_versions.order_by("-version").first()
        if latest is None or latest.schema != campos:
            next_version = (latest.version + 1) if latest else 1
            ExamenSchemaVersion.objects.create(
                examen=examen,
                version=next_version,
                schema=campos,
                created_by=admin,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✔ Schema publicado v{next_version} para '{examen.nombre}'"
                )
            )
        else:
            self.stdout.write(
                f"  - Schema v{latest.version} ya vigente para '{examen.nombre}'"
            )
        return examen

    def _assign_examenes_to_tipo_visita(
        self, tipo_visita: TipoVisita, examenes: list[Examen]
    ):
        ids_actuales = set()
        if isinstance(tipo_visita.examenes, list):
            for item in tipo_visita.examenes:
                try:
                    ids_actuales.add(int(item.get("id")))
                except (TypeError, ValueError, AttributeError):
                    continue
        nuevo = list(tipo_visita.examenes or []) if isinstance(
            tipo_visita.examenes, list
        ) else []
        added = 0
        for examen in examenes:
            if examen.id in ids_actuales:
                continue
            nuevo.append({"id": examen.id, "nombre": examen.nombre})
            added += 1
        if added:
            tipo_visita.examenes = nuevo
            tipo_visita.save(update_fields=["examenes"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✔ {added} examen(es) asignados al TipoVisita"
                )
            )
        else:
            self.stdout.write("  - Exámenes ya asignados al TipoVisita")

    def _ensure_visita(
        self, paciente: DatosDemograficos, tipo_visita: TipoVisita, admin
    ) -> Visita:
        visita = Visita.objects.filter(
            paciente=paciente, Tipo_visita=tipo_visita
        ).first()
        if visita:
            self.stdout.write(f"  - Visita existente: #{visita.id}")
            return visita
        visita = Visita.objects.create(
            paciente=paciente,
            nombre=f"Demo {DEMO_TIPO_VISITA}",
            Tipo_visita=tipo_visita,
            fecha=date.today(),
            evaluador=admin,
            estado_visita="abierta",
            firmado=False,
        )
        self.stdout.write(self.style.SUCCESS(f"  ✔ Visita creada: #{visita.id}"))
        return visita

    def _ensure_visita_examenes(self, visita: Visita, examenes: list[Examen]):
        created_count = 0
        for examen in examenes:
            _, created = VisitaExamen.objects.get_or_create(
                visita=visita,
                examen=examen,
                defaults={"estado": "pendiente"},
            )
            if created:
                created_count += 1
        if created_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✔ {created_count} VisitaExamen creado(s)"
                )
            )
        else:
            self.stdout.write("  - VisitaExamen ya existían")

    def _print_summary(self, *, admin, proyecto, tipo_visita, paciente, visita, examenes):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== RESUMEN ==="))
        self.stdout.write(f"Usuario admin: {admin.username} (superuser)")
        self.stdout.write(f"Proyecto:      {proyecto.nombre} (id={proyecto.id})")
        self.stdout.write(
            f"TipoVisita:    {tipo_visita.nombre} (id={tipo_visita.id})"
        )
        self.stdout.write(
            f"Paciente:      {paciente.primer_nombre} {paciente.primer_apellido} "
            f"(id={paciente.id}, doc={paciente.numero_documento})"
        )
        self.stdout.write(f"Visita:        #{visita.id}")
        self.stdout.write("Exámenes builder:")
        for ex in examenes:
            self.stdout.write(f"  - {ex.nombre} (id={ex.id}, categoría={ex.categoria})")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Siguientes pasos:"))
        self.stdout.write(
            "  1. Abre http://localhost:8000/ y entra con tu superusuario."
        )
        self.stdout.write(
            "  2. Ve al menú 'Form Builder' (sidenav, solo visible para staff) "
            "para ver y editar schemas."
        )
        self.stdout.write(
            f"  3. Abre la visita del paciente y realiza los exámenes demo."
        )
