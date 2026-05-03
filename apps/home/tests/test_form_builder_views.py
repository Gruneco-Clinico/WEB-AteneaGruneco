# -*- encoding: utf-8 -*-
"""
Tests de integración de vistas y modelos del Form Builder.

Cubre:
- ``ensure_schema_version``: idempotencia (no crear nueva versión si el JSON
  no cambió) y autoincremento del número de versión.
- ``exam_builder_create`` / ``exam_builder_edit``: validación de JSON y
  persistencia.
- ``exam_builder_publish``: publica versión.
- ``exam_builder_preview``: rechaza JSON inválido y devuelve HTML válido.
- ``guardar_examen_builder``: errores de validación → redirect; éxito →
  ``ExamenSubmission`` con ``answers``/``computed`` y transición de estado de
  ``VisitaExamen`` a ``completado``.
- Visita firmada → no permite guardar.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.home.models import (
    DatosDemograficos,
    Examen,
    ExamenSchemaVersion,
    ExamenSubmission,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
)
from apps.home.views.exam_builder import ensure_schema_version


def _make_paciente(**overrides):
    defaults = dict(
        primer_nombre="Juan",
        primer_apellido="Pérez",
        numero_documento="100" + str(DatosDemograficos.objects.count() + 1).zfill(7),
        celular="300" + str(DatosDemograficos.objects.count() + 1).zfill(7),
        fecha_nacimiento="1980-01-01",
        edad=46,
        ocupacion="Ingeniero",
        religion="Católico",
        eps="Sura",
        correo=f"j{DatosDemograficos.objects.count()}@test.com",
    )
    defaults.update(overrides)
    return DatosDemograficos.objects.create(**defaults)


def _make_visita(paciente, firmado=False):
    proyecto = Proyecto.objects.create(nombre=f"Proy-{Proyecto.objects.count()}")
    tipo = TipoVisita.objects.create(nombre="Inicial", proyecto=proyecto, examenes=[])
    return Visita.objects.create(
        paciente=paciente,
        nombre="Visita test",
        Tipo_visita=tipo,
        fecha="2026-01-01",
        firmado=firmado,
    )


class EnsureSchemaVersionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")
        self.examen = Examen.objects.create(
            nombre="Demo", categoria="OTROS", campos=[],
        )

    def test_creates_first_version_when_none_exists(self):
        self.examen.campos = [{"type": "text", "id": "a", "label": "A"}]
        self.examen.save()
        sv = ensure_schema_version(self.examen, self.user)
        self.assertEqual(sv.version, 1)
        self.assertEqual(sv.schema, self.examen.campos)

    def test_idempotent_when_schema_unchanged(self):
        self.examen.campos = [{"type": "text", "id": "a"}]
        self.examen.save()
        v1 = ensure_schema_version(self.examen, self.user)
        v2 = ensure_schema_version(self.examen, self.user)
        self.assertEqual(v1.pk, v2.pk)
        self.assertEqual(
            ExamenSchemaVersion.objects.filter(examen=self.examen).count(), 1
        )

    def test_creates_new_version_when_schema_changes(self):
        self.examen.campos = [{"type": "text", "id": "a"}]
        self.examen.save()
        ensure_schema_version(self.examen, self.user)

        self.examen.campos = [
            {"type": "text", "id": "a"},
            {"type": "number", "id": "b"},
        ]
        self.examen.save()
        v2 = ensure_schema_version(self.examen, self.user)
        self.assertEqual(v2.version, 2)
        self.assertEqual(
            ExamenSchemaVersion.objects.filter(examen=self.examen).count(), 2
        )

    def test_idempotent_when_keys_reordered(self):
        """Reordenar claves del JSON no debe crear una nueva versión."""
        self.examen.campos = [{"id": "a", "type": "text", "label": "A"}]
        self.examen.save()
        ensure_schema_version(self.examen, self.user)

        # mismo contenido, otro orden de claves
        self.examen.campos = [{"type": "text", "label": "A", "id": "a"}]
        self.examen.save()
        ensure_schema_version(self.examen, self.user)

        self.assertEqual(
            ExamenSchemaVersion.objects.filter(examen=self.examen).count(), 1
        )


class ExamBuilderAdminViewsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            "admin", password="x", is_staff=True
        )
        self.client = Client()
        self.client.force_login(self.staff)
        self.examen = Examen.objects.create(
            nombre="Demo", categoria="OTROS", campos=[],
        )

    # --- create ---------------------------------------------------------
    def test_create_requires_nombre(self):
        resp = self.client.post(reverse("exam_builder_create"), {"nombre": "  "})
        self.assertEqual(resp.status_code, 302)
        # Debe redirigir al mismo create (no se creó el examen)
        # (Se valida indirectamente por count.)
        self.assertEqual(Examen.objects.filter(nombre="  ").count(), 0)

    def test_create_persists_examen(self):
        resp = self.client.post(reverse("exam_builder_create"), {
            "nombre": "Nuevo Examen",
            "categoria": "OTROS",
            "descripcion": "descripcion",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Examen.objects.filter(nombre="Nuevo Examen").exists())

    # --- edit -----------------------------------------------------------
    def test_edit_rejects_invalid_json(self):
        resp = self.client.post(
            reverse("exam_builder_edit", kwargs={"pk": self.examen.pk}),
            {"campos_json": "{ not-json"},
        )
        self.assertEqual(resp.status_code, 302)
        # El examen no debe haber recibido los campos malformados.
        self.examen.refresh_from_db()
        self.assertEqual(self.examen.campos, [])

    def test_edit_accepts_valid_list(self):
        payload = '[{"type":"text","id":"a","label":"A"}]'
        resp = self.client.post(
            reverse("exam_builder_edit", kwargs={"pk": self.examen.pk}),
            {"campos_json": payload, "nombre": "Demo", "categoria": "OTROS"},
        )
        self.assertEqual(resp.status_code, 302)
        self.examen.refresh_from_db()
        self.assertEqual(len(self.examen.campos), 1)

    def test_edit_with_publicar_creates_version(self):
        payload = '[{"type":"text","id":"a","label":"A"}]'
        self.client.post(
            reverse("exam_builder_edit", kwargs={"pk": self.examen.pk}),
            {
                "campos_json": payload, "nombre": "Demo",
                "categoria": "OTROS", "publicar": "1",
            },
        )
        self.assertEqual(
            ExamenSchemaVersion.objects.filter(examen=self.examen).count(), 1
        )

    # --- preview --------------------------------------------------------
    def test_preview_rejects_invalid_json(self):
        resp = self.client.post(
            reverse("exam_builder_preview"), {"campos_json": "{not json"}
        )
        self.assertEqual(resp.status_code, 400)

    def test_preview_returns_html_for_valid_schema(self):
        payload = '[{"type":"text","id":"a","label":"A"}]'
        resp = self.client.post(
            reverse("exam_builder_preview"),
            {"campos_json": payload, "titulo_preview": "Vista previa"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertIn('name="a"', body["html"])

    def test_preview_requires_post(self):
        resp = self.client.get(reverse("exam_builder_preview"))
        self.assertEqual(resp.status_code, 403)

    # --- publish --------------------------------------------------------
    def test_publish_idempotent(self):
        self.examen.campos = [{"type": "text", "id": "a"}]
        self.examen.save()
        url = reverse("exam_builder_publish", kwargs={"pk": self.examen.pk})
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            ExamenSchemaVersion.objects.filter(examen=self.examen).count(), 1
        )


class GuardarExamenBuilderTests(TestCase):
    """Integración del endpoint que guarda las respuestas de un examen."""

    def setUp(self):
        self.user = User.objects.create_user("evaluador", password="x")
        self.client = Client()
        self.client.force_login(self.user)

        self.paciente = _make_paciente()
        self.visita = _make_visita(self.paciente)
        self.examen = Examen.objects.create(
            nombre="IMC test", categoria="OTROS", campos=[
                {"type": "number", "id": "peso_kg", "label": "Peso",
                 "required": True},
                {"type": "number", "id": "talla_cm", "label": "Talla",
                 "required": True},
                {"type": "computed", "id": "imc", "formula": "imc",
                 "depends_on": ["peso_kg", "talla_cm"]},
            ],
        )
        self.visita_examen = VisitaExamen.objects.create(
            visita=self.visita, examen=self.examen, estado="pendiente",
        )

    def _post_payload(self, **overrides):
        data = {
            "visita_id": self.visita.id,
            "paciente_id": self.paciente.id,
            "examen_id": self.examen.id,
            "peso_kg": "70",
            "talla_cm": "170",
        }
        data.update(overrides)
        return data

    def test_save_success_creates_submission_and_completes(self):
        resp = self.client.post(
            reverse("guardar_examen_builder"), self._post_payload()
        )
        self.assertEqual(resp.status_code, 302)

        sub = ExamenSubmission.objects.get(visita_examen=self.visita_examen)
        self.assertEqual(sub.answers, {"peso_kg": 70, "talla_cm": 170})
        self.assertEqual(sub.computed, {"imc": 24.22})

        self.visita_examen.refresh_from_db()
        self.assertEqual(self.visita_examen.estado, "completado")
        self.assertIsNotNone(self.visita_examen.fecha_completado)

    def test_save_validation_error_does_not_create_submission(self):
        resp = self.client.post(
            reverse("guardar_examen_builder"),
            self._post_payload(peso_kg=""),  # required missing
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            ExamenSubmission.objects.filter(
                visita_examen=self.visita_examen
            ).exists()
        )

    def test_save_blocked_when_visita_firmada(self):
        self.visita.firmado = True
        self.visita.save()
        resp = self.client.post(
            reverse("guardar_examen_builder"), self._post_payload()
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            ExamenSubmission.objects.filter(
                visita_examen=self.visita_examen
            ).exists()
        )

    def test_save_freezes_schema_version_at_save_time(self):
        """La submission debe quedar atada a la versión del esquema vigente,
        no a una futura versión publicada después."""
        self.client.post(
            reverse("guardar_examen_builder"), self._post_payload()
        )
        sub = ExamenSubmission.objects.get(visita_examen=self.visita_examen)
        v_inicial = sub.schema_version

        # Ahora se cambia el esquema y se publica nueva versión.
        self.examen.campos = self.examen.campos + [
            {"type": "text", "id": "extra", "label": "Extra"},
        ]
        self.examen.save()
        ensure_schema_version(self.examen, self.user)

        sub.refresh_from_db()
        self.assertEqual(sub.schema_version_id, v_inicial.id)

    def test_save_updates_existing_submission(self):
        """Re-guardar el mismo examen actualiza la submission existente."""
        self.client.post(
            reverse("guardar_examen_builder"), self._post_payload()
        )
        self.client.post(
            reverse("guardar_examen_builder"),
            self._post_payload(peso_kg="80"),
        )
        subs = ExamenSubmission.objects.filter(
            visita_examen=self.visita_examen
        )
        self.assertEqual(subs.count(), 1)
        self.assertEqual(subs.first().answers["peso_kg"], 80)


class ExamenSubmissionConstraintsTests(TestCase):
    def setUp(self):
        self.paciente = _make_paciente()
        self.visita = _make_visita(self.paciente)
        self.examen = Examen.objects.create(nombre="X", categoria="OTROS")
        self.ve = VisitaExamen.objects.create(
            visita=self.visita, examen=self.examen
        )

    def test_one_to_one_constraint(self):
        ExamenSubmission.objects.create(visita_examen=self.ve, answers={})
        with self.assertRaises(Exception):
            ExamenSubmission.objects.create(visita_examen=self.ve, answers={})


class ExamenSchemaVersionConstraintsTests(TestCase):
    def setUp(self):
        self.examen = Examen.objects.create(nombre="X", categoria="OTROS")

    def test_unique_together_examen_version(self):
        ExamenSchemaVersion.objects.create(
            examen=self.examen, version=1, schema=[]
        )
        with self.assertRaises(Exception):
            ExamenSchemaVersion.objects.create(
                examen=self.examen, version=1, schema=[]
            )
