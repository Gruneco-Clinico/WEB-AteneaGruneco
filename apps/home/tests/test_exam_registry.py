# -*- encoding: utf-8 -*-
from django.test import TestCase
from django.apps import apps

from apps.home.exam_registry import (
    EXAM_REGISTRY,
    ALL_EXAM_IDS,
    get_exam_config,
    get_exam_model,
    get_all_related_names,
)


class ExamRegistryDataTest(TestCase):
    """Tests for the static EXAM_REGISTRY data structure."""

    def test_registry_has_37_entries(self):
        """37 exams (IDs 3-40, no ID 6)."""
        self.assertEqual(len(EXAM_REGISTRY), 37)

    def test_all_exam_ids_sorted(self):
        self.assertEqual(ALL_EXAM_IDS, sorted(EXAM_REGISTRY.keys()))

    def test_no_id_6(self):
        self.assertNotIn(6, EXAM_REGISTRY)

    def test_every_entry_has_required_keys(self):
        required = {"model_name", "template", "related_name"}
        for exam_id, config in EXAM_REGISTRY.items():
            with self.subTest(exam_id=exam_id):
                self.assertTrue(
                    required.issubset(config.keys()),
                    f"Exam {exam_id} missing keys: {required - config.keys()}",
                )

    def test_cuestionarios_has_no_model(self):
        config = EXAM_REGISTRY[11]
        self.assertIsNone(config["model_name"])
        self.assertIsNone(config["related_name"])

    def test_antecedentes_uses_bridge(self):
        config = EXAM_REGISTRY[5]
        self.assertTrue(config.get("use_bridge"))
        self.assertIsNone(config["related_name"])

    def test_cognitivo_anamnesis_custom_related_name(self):
        config = EXAM_REGISTRY[20]
        self.assertEqual(config["related_name"], "cognitivo_anamnesis_resultado")

    def test_revision_sistemas_corrected_related_name(self):
        """Verify the typo 'revisionsistemrasresult' has been fixed."""
        config = EXAM_REGISTRY[4]
        self.assertEqual(config["related_name"], "revisionsistemasresult_resultado")
        self.assertNotIn("sistemras", config["related_name"])


class GetExamConfigTest(TestCase):
    """Tests for get_exam_config()."""

    def test_returns_config_for_valid_id(self):
        config = get_exam_config(13)
        self.assertEqual(config["model_name"], "PittsburghResult")
        self.assertEqual(config["template"], "examenes_sueno/sueno_Pitsburg.html")

    def test_returns_none_for_invalid_id(self):
        self.assertIsNone(get_exam_config(999))

    def test_accepts_string_id(self):
        config = get_exam_config("13")
        self.assertIsNotNone(config)
        self.assertEqual(config["model_name"], "PittsburghResult")


class GetExamModelTest(TestCase):
    """Tests for get_exam_model() lazy resolution."""

    def test_resolves_model_class(self):
        model = get_exam_model(13)
        self.assertEqual(model.__name__, "PittsburghResult")
        self.assertEqual(model._meta.app_label, "home")

    def test_returns_none_for_no_model(self):
        self.assertIsNone(get_exam_model(11))

    def test_returns_none_for_invalid_id(self):
        self.assertIsNone(get_exam_model(999))

    def test_all_model_names_resolve(self):
        """Every model_name in the registry must resolve to a real Django model."""
        for exam_id, config in EXAM_REGISTRY.items():
            if config["model_name"] is None:
                continue
            with self.subTest(exam_id=exam_id, model=config["model_name"]):
                model = apps.get_model("home", config["model_name"])
                self.assertIsNotNone(model, f"Model {config['model_name']} not found")


class GetAllRelatedNamesTest(TestCase):
    """Tests for get_all_related_names()."""

    def test_excludes_none_entries(self):
        names = get_all_related_names()
        self.assertNotIn(None, names)

    def test_count_matches_exams_with_related_names(self):
        expected = sum(
            1 for v in EXAM_REGISTRY.values() if v.get("related_name")
        )
        self.assertEqual(len(get_all_related_names()), expected)

    def test_contains_known_entries(self):
        names = get_all_related_names()
        self.assertIn("pittsburghresult_resultado", names)
        self.assertIn("cognitivo_anamnesis_resultado", names)
        self.assertIn("revisionsistemasresult_resultado", names)

    def test_does_not_contain_old_typo(self):
        names = get_all_related_names()
        self.assertNotIn("revisionsistemrasresult_resultado", names)
