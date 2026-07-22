# -*- encoding: utf-8 -*-
"""Tests C-15: exportación CSV con selección de campos por examen."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.home.models import (
    AQDCuidadorResult,
    DatosDemograficos,
    Examen,
    MEWResult,
    PuntajeCDRResult,
)
from apps.home.services.project_csv_export import (
    ExportField,
    ExamExportCatalog,
    _builder_repeater_json,
    build_exam_export_catalog,
    extract_exam_value,
    get_builder_export_fields,
    get_legacy_export_fields,
    parse_export_selection,
    serialize_csv_value,
    serialize_demographic_value,
)


class FakePost(dict):
    def getlist(self, key):
        val = self.get(key, [])
        if isinstance(val, list):
            return val
        return [val]


class SerializeValueTests(SimpleTestCase):
    def test_preserva_cero_y_false(self):
        self.assertEqual(serialize_csv_value(0), "0")
        self.assertEqual(serialize_csv_value(False), "No")
        self.assertEqual(serialize_csv_value(True), "Sí")
        self.assertEqual(serialize_csv_value(None), "")


class CatalogLegacyTests(SimpleTestCase):
    def test_aqd_tiene_total_e_items(self):
        exam = Examen(id=30, nombre="AQD Cuidador")
        fields = get_legacy_export_fields(exam)
        keys = {f.key for f in fields}
        self.assertIn("summary:puntaje_total", keys)
        self.assertTrue(any(f.group == "item" for f in fields))
        total = next(f for f in fields if f.key == "summary:puntaje_total")
        self.assertTrue(total.default_selected)

    def test_cdr_summary_fields(self):
        exam = Examen(id=35, nombre="CDR")
        keys = {f.key for f in get_legacy_export_fields(exam)}
        self.assertIn("summary:cdr_global", keys)
        self.assertIn("summary:suma_cajas", keys)

    def test_redlat_componentes(self):
        exam = Examen(id=32, nombre="RedLat")
        keys = {f.key for f in get_legacy_export_fields(exam)}
        self.assertIn("summary:puntaje_total", keys)
        self.assertIn("summary:puntaje_autocuidado", keys)

    def test_mew_puntuacion(self):
        exam = Examen(id=16, nombre="MEW")
        keys = {f.key for f in get_legacy_export_fields(exam)}
        self.assertIn("summary:puntuacion", keys)

    def test_anamnesis_no_default(self):
        exam = Examen(id=10, nombre="Anamnesis sueño")
        cat = build_exam_export_catalog([exam])[0]
        self.assertFalse(cat.default_selected)


class BuilderCatalogTests(SimpleTestCase):
    def test_builder_answers_computed_repeater(self):
        exam = Examen(
            id=9999,
            nombre="Builder demo",
            campos=[
                {
                    "type": "section",
                    "label": "S1",
                    "fields": [
                        {"id": "item_1", "type": "number", "label": "Ítem 1"},
                        {
                            "id": "gran_total",
                            "type": "computed",
                            "label": "Puntaje total",
                            "export_role": "total",
                        },
                        {
                            "id": "meds",
                            "type": "repeater",
                            "label": "Medicamentos",
                            "fields": [
                                {"id": "nombre", "type": "text", "label": "Nombre"},
                            ],
                        },
                    ],
                }
            ],
        )
        fields = get_builder_export_fields(exam)
        keys = {f.key for f in fields}
        self.assertIn("answer:item_1", keys)
        self.assertIn("computed:gran_total", keys)
        self.assertIn("repeater:meds", keys)
        total = next(f for f in fields if f.key == "computed:gran_total")
        self.assertEqual(total.group, "summary")
        self.assertTrue(total.default_selected)


class ParseSelectionTests(SimpleTestCase):
    def _catalog(self):
        return [
            ExamExportCatalog(
                examen_id=30,
                examen_nombre="AQD",
                fields=[
                    ExportField(
                        "summary:puntaje_total",
                        "Puntaje total",
                        "summary",
                        "legacy",
                        "puntaje_total",
                        True,
                    ),
                    ExportField(
                        "item:firmar", "Firmar", "item", "legacy", "firmar", False
                    ),
                ],
                default_selected=True,
            ),
            ExamExportCatalog(
                examen_id=35,
                examen_nombre="CDR",
                fields=[
                    ExportField(
                        "summary:cdr_global",
                        "CDR Global",
                        "summary",
                        "legacy",
                        "cdr_global",
                        True,
                    ),
                ],
                default_selected=True,
            ),
        ]

    def test_namespaced_selection(self):
        post = FakePost(
            {
                "examenes": ["30"],
                "campos_examen_30": [
                    "summary:puntaje_total",
                    "item:firmar",
                    "hacker:x",
                ],
            }
        )
        sel = parse_export_selection(post, self._catalog())
        self.assertEqual(list(sel.keys()), [30])
        self.assertEqual(
            [f.key for f in sel[30]], ["summary:puntaje_total", "item:firmar"]
        )

    def test_fallback_global_campos_examen(self):
        post = FakePost(
            {
                "examenes": ["30", "35"],
                "campos_examen": ["puntaje_total", "cdr_global"],
            }
        )
        sel = parse_export_selection(post, self._catalog())
        self.assertEqual([f.key for f in sel[30]], ["summary:puntaje_total"])
        self.assertEqual([f.key for f in sel[35]], ["summary:cdr_global"])


class ExtractLegacyTests(SimpleTestCase):
    def test_aqd_solo_total_y_cero(self):
        resultado = AQDCuidadorResult(puntaje_total=0, firmar="0")
        ve = MagicMock()
        ve.get_resultado_instance.return_value = resultado
        spec = ExportField(
            "summary:puntaje_total",
            "Puntaje total",
            "summary",
            "legacy",
            "puntaje_total",
        )
        self.assertEqual(extract_exam_value(ve, spec), "0")

    def test_aqd_item(self):
        resultado = AQDCuidadorResult(firmar="1", puntaje_total=5)
        ve = MagicMock()
        ve.get_resultado_instance.return_value = resultado
        spec = ExportField("item:firmar", "Firmar", "item", "legacy", "firmar")
        self.assertEqual(extract_exam_value(ve, spec), "1")

    def test_cdr_suma_cajas_en_vivo(self):
        resultado = PuntajeCDRResult(
            cdr_memoria="1",
            cdr_orientacion="1",
            cdr_juicio="1",
            cdr_comunitarias="0.5",
            cdr_pasatiempos="0.5",
            cdr_cuidado="1",
            cdr_global="1",
            suma_cajas=0,
        )
        ve = MagicMock()
        ve.get_resultado_instance.return_value = resultado
        spec = ExportField(
            "summary:suma_cajas", "Suma", "summary", "legacy", "suma_cajas"
        )
        self.assertEqual(extract_exam_value(ve, spec), "5.0")

    def test_cdr_global(self):
        resultado = PuntajeCDRResult(cdr_global="2")
        ve = MagicMock()
        ve.get_resultado_instance.return_value = resultado
        spec = ExportField(
            "summary:cdr_global", "CDR Global", "summary", "legacy", "cdr_global"
        )
        self.assertEqual(extract_exam_value(ve, spec), "2")

    def test_mew_puntuacion(self):
        resultado = MEWResult(puntuacion=49, tipo_persona="Intermedio")
        ve = MagicMock()
        ve.get_resultado_instance.return_value = resultado
        spec = ExportField(
            "summary:puntuacion",
            "Puntuación total MEQ",
            "summary",
            "legacy",
            "puntuacion",
        )
        self.assertEqual(extract_exam_value(ve, spec), "49")


class BuilderExtractTests(SimpleTestCase):
    def test_repeater_json(self):
        schema = [
            {
                "id": "meds",
                "type": "repeater",
                "label": "Meds",
                "fields": [{"id": "nombre", "type": "text", "label": "Nombre"}],
            }
        ]
        out = _builder_repeater_json(
            {"meds": [{"nombre": "Ibuprofeno"}]}, "meds", schema
        )
        self.assertIn("Ibuprofeno", out)
        self.assertIn("parametro", out)
        self.assertIn("Nombre", out)

    def _mock_submission_qs(self, submission):
        qs = MagicMock()
        qs.select_related.return_value.order_by.return_value.first.return_value = (
            submission
        )
        return qs

    def test_builder_computed_cero(self):
        ve = MagicMock()
        submission = MagicMock()
        submission.answers = {}
        submission.computed = {"total": 0}
        submission.schema_version_id = None
        submission.schema_version = None
        ve.examen.campos = [{"id": "total", "type": "computed", "label": "Total"}]

        with patch(
            "apps.home.models.ExamenSubmission.objects.filter",
            return_value=self._mock_submission_qs(submission),
        ):
            spec = ExportField(
                "computed:total", "Total", "summary", "builder", "total"
            )
            self.assertEqual(extract_exam_value(ve, spec), "0")

    def test_builder_answer(self):
        ve = MagicMock()
        submission = MagicMock()
        submission.answers = {"item_1": False}
        submission.computed = {}
        submission.schema_version_id = None
        submission.schema_version = None
        ve.examen.campos = []

        with patch(
            "apps.home.models.ExamenSubmission.objects.filter",
            return_value=self._mock_submission_qs(submission),
        ):
            spec = ExportField(
                "answer:item_1", "Ítem 1", "item", "builder", "item_1"
            )
            self.assertEqual(extract_exam_value(ve, spec), "No")


class DemographicSerializeTests(SimpleTestCase):
    def test_edad_cero_no_vacia(self):
        p = DatosDemograficos(
            primer_nombre="X",
            primer_apellido="Y",
            numero_documento="Z",
            fecha_nacimiento="2026-01-01",
            edad=0,
            celular="1",
        )
        self.assertEqual(serialize_demographic_value(p, "edad"), "0")
