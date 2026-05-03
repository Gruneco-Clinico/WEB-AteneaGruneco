# -*- encoding: utf-8 -*-
"""
Tests unitarios del lenguaje de esquema del Form Builder.

Cubre:
- ``normalize_schema``: tolerancia a entradas heterogéneas.
- ``visible_when_match``: operadores ``equals`` / ``not_equals`` / ``contains``
  + coerciones boolean / string.
- ``_parse_simple_value``: coerción por tipo (number, checkbox, multiselect…).
- ``_validate_leaf``: ``required``, ``min``/``max``.
- ``parse_post_to_answers`` y ``validate_and_parse_post``: integración POST →
  respuestas, repeaters, secciones ocultas que NO deben validar hijos.
- ``apply_computed``: caso especial IMC + fórmulas genéricas con ``precision``,
  división por cero, dependencias ausentes/no numéricas.

Estos tests usan ``SimpleTestCase`` porque NO requieren BD: prueban funciones
puras del módulo ``apps.home.form_builder.schema``.
"""

from django.http import QueryDict
from django.test import SimpleTestCase

from apps.home.form_builder.schema import (
    _parse_simple_value,
    _safe_eval_arithmetic,
    _validate_leaf,
    apply_computed,
    normalize_schema,
    parse_post_to_answers,
    validate_and_parse_post,
    visible_when_match,
)


def _qd(data):
    """Construye un ``QueryDict`` real (con soporte de ``getlist``)."""
    qd = QueryDict(mutable=True)
    for k, v in data.items():
        if isinstance(v, list):
            qd.setlist(k, v)
        else:
            qd[k] = v
    return qd


# ---------------------------------------------------------------------------
# normalize_schema
# ---------------------------------------------------------------------------


class NormalizeSchemaTests(SimpleTestCase):
    def test_none_returns_empty_list(self):
        self.assertEqual(normalize_schema(None), [])

    def test_dict_with_fields_unwraps(self):
        out = normalize_schema({"fields": [{"type": "text", "id": "a"}]})
        self.assertEqual(out, [{"type": "text", "id": "a"}])

    def test_non_list_returns_empty(self):
        self.assertEqual(normalize_schema("no soy lista"), [])
        self.assertEqual(normalize_schema(42), [])

    def test_assigns_default_id_when_missing(self):
        out = normalize_schema([{"type": "text"}])
        self.assertEqual(out[0]["id"], "field_0")

    def test_assigns_default_section_label(self):
        out = normalize_schema([{"type": "section"}])
        self.assertTrue(out[0]["label"].startswith("Sección"))

    def test_skips_non_dict_entries(self):
        out = normalize_schema([{"type": "text", "id": "a"}, "garbage", 42, None])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], "a")

    def test_preserves_existing_id_and_label(self):
        out = normalize_schema([
            {"type": "section", "id": "sec1", "label": "Mi sección"},
        ])
        self.assertEqual(out[0]["label"], "Mi sección")


# ---------------------------------------------------------------------------
# visible_when_match
# ---------------------------------------------------------------------------


class VisibleWhenMatchTests(SimpleTestCase):
    def _node(self, cond):
        return {"visible_when": cond}

    # --- equals (default) -------------------------------------------------
    def test_equals_match(self):
        self.assertTrue(
            visible_when_match(self._node({"field": "fuma", "equals": "si"}),
                               {"fuma": "si"})
        )

    def test_equals_no_match(self):
        self.assertFalse(
            visible_when_match(self._node({"field": "fuma", "equals": "si"}),
                               {"fuma": "no"})
        )

    def test_equals_field_missing(self):
        self.assertFalse(
            visible_when_match(self._node({"field": "fuma", "equals": "si"}),
                               {})
        )

    # --- not_equals -------------------------------------------------------
    def test_not_equals_match(self):
        self.assertTrue(
            visible_when_match(
                self._node({"field": "tipo", "op": "not_equals", "value": "A"}),
                {"tipo": "B"},
            )
        )

    def test_not_equals_no_match(self):
        self.assertFalse(
            visible_when_match(
                self._node({"field": "tipo", "op": "not_equals", "value": "A"}),
                {"tipo": "A"},
            )
        )

    # --- contains ---------------------------------------------------------
    def test_contains_in_list(self):
        self.assertTrue(
            visible_when_match(
                self._node({"field": "tags", "op": "contains", "value": "rojo"}),
                {"tags": ["rojo", "azul"]},
            )
        )

    def test_contains_not_in_list(self):
        self.assertFalse(
            visible_when_match(
                self._node({"field": "tags", "op": "contains", "value": "verde"}),
                {"tags": ["rojo", "azul"]},
            )
        )

    def test_contains_substring_string(self):
        self.assertTrue(
            visible_when_match(
                self._node({"field": "obs", "op": "contains", "value": "urg"}),
                {"obs": "es urgente revisar"},
            )
        )

    def test_contains_with_none_actual(self):
        self.assertFalse(
            visible_when_match(
                self._node({"field": "obs", "op": "contains", "value": "x"}),
                {},
            )
        )

    # --- boolean coercion -------------------------------------------------
    def test_equals_true_boolean(self):
        self.assertTrue(
            visible_when_match(self._node({"field": "ok", "equals": True}),
                               {"ok": True})
        )
        # truthy non-bool también satisface (bool(actual)==True)
        self.assertTrue(
            visible_when_match(self._node({"field": "ok", "equals": True}),
                               {"ok": "on"})
        )

    def test_equals_false_boolean(self):
        self.assertTrue(
            visible_when_match(self._node({"field": "ok", "equals": False}),
                               {"ok": ""})
        )
        self.assertTrue(
            visible_when_match(self._node({"field": "ok", "equals": False}),
                               {"ok": 0})
        )

    # --- borde ------------------------------------------------------------
    def test_no_visible_when_means_visible(self):
        self.assertTrue(visible_when_match({}, {}))

    def test_no_field_means_visible(self):
        # Sin "field" en la condición, se considera visible.
        self.assertTrue(
            visible_when_match(self._node({"equals": "x"}), {})
        )

    def test_legacy_alias_value_overrides_equals(self):
        # ``value`` tiene prioridad si ambos están presentes.
        self.assertTrue(
            visible_when_match(
                self._node({"field": "x", "equals": "wrong", "value": "ok"}),
                {"x": "ok"},
            )
        )


# ---------------------------------------------------------------------------
# _parse_simple_value
# ---------------------------------------------------------------------------


class ParseSimpleValueTests(SimpleTestCase):
    def test_number_with_comma_decimal(self):
        self.assertEqual(_parse_simple_value({"type": "number"}, "70,5"), 70.5)

    def test_number_integer_kept_as_int(self):
        v = _parse_simple_value({"type": "number"}, "70")
        self.assertEqual(v, 70)
        self.assertIsInstance(v, int)

    def test_number_invalid_returns_raw(self):
        self.assertEqual(_parse_simple_value({"type": "number"}, "abc"), "abc")

    def test_number_empty_returns_none(self):
        self.assertIsNone(_parse_simple_value({"type": "number"}, ""))
        self.assertIsNone(_parse_simple_value({"type": "number"}, None))

    def test_checkbox_truthy_values(self):
        node = {"type": "checkbox"}
        for raw in ("on", "true", "True", "1", True, 1):
            self.assertTrue(_parse_simple_value(node, raw),
                            f"esperaba True para {raw!r}")
        self.assertFalse(_parse_simple_value(node, ""))
        self.assertFalse(_parse_simple_value(node, None))
        self.assertFalse(_parse_simple_value(node, "off"))

    def test_boolean_coercion(self):
        node = {"type": "boolean"}
        self.assertTrue(_parse_simple_value(node, "true"))
        self.assertTrue(_parse_simple_value(node, "1"))
        self.assertFalse(_parse_simple_value(node, "false"))
        self.assertFalse(_parse_simple_value(node, ""))

    def test_multiselect_normalizes_to_list_of_str(self):
        out = _parse_simple_value({"type": "multiselect"}, [1, "a", "", None])
        self.assertEqual(out, ["1", "a"])

    def test_multiselect_none_returns_empty_list(self):
        self.assertEqual(_parse_simple_value({"type": "multiselect"}, None), [])

    def test_text_strips_whitespace(self):
        self.assertEqual(_parse_simple_value({"type": "text"}, "  hola  "), "hola")


# ---------------------------------------------------------------------------
# _validate_leaf
# ---------------------------------------------------------------------------


class ValidateLeafTests(SimpleTestCase):
    def test_required_text_missing(self):
        err = _validate_leaf(
            {"type": "text", "label": "Nombre", "required": True}, ""
        )
        self.assertIn("Nombre", err)

    def test_required_multiselect_empty_list(self):
        err = _validate_leaf(
            {"type": "multiselect", "label": "Síntomas", "required": True}, []
        )
        self.assertIn("Síntomas", err)

    def test_number_min(self):
        err = _validate_leaf(
            {"type": "number", "label": "Edad", "min": 0}, -1
        )
        self.assertIsNotNone(err)
        self.assertIn("≥ 0", err)

    def test_number_max(self):
        err = _validate_leaf(
            {"type": "number", "label": "Edad", "max": 120}, 150
        )
        self.assertIsNotNone(err)
        self.assertIn("≤ 120", err)

    def test_number_within_range_is_ok(self):
        self.assertIsNone(
            _validate_leaf({"type": "number", "min": 0, "max": 120}, 30)
        )

    def test_number_non_numeric_value(self):
        err = _validate_leaf({"type": "number", "label": "X"}, "abc")
        self.assertIsNotNone(err)
        self.assertIn("numérico", err)


# ---------------------------------------------------------------------------
# parse_post_to_answers / validate_and_parse_post (integración)
# ---------------------------------------------------------------------------


class ParsePostTests(SimpleTestCase):
    def test_required_field_missing_emits_error(self):
        schema = [{"type": "text", "id": "nombre", "label": "Nombre",
                   "required": True}]
        _, errors = parse_post_to_answers(schema, _qd({}))
        self.assertTrue(any("Nombre" in e for e in errors))

    def test_hidden_section_skips_required_inside(self):
        """Si la sección padre está oculta, NO debe validar sus hijos."""
        schema = [
            {"type": "select", "id": "fuma", "label": "Fuma",
             "options": ["si", "no"]},
            {"type": "section", "label": "Detalle fumador",
             "visible_when": {"field": "fuma", "equals": "si"},
             "fields": [
                 {"type": "number", "id": "cigs", "label": "Cigs/día",
                  "required": True},
             ]},
        ]
        ans, errors = parse_post_to_answers(schema, _qd({"fuma": "no"}))
        self.assertEqual(errors, [])
        self.assertEqual(ans["fuma"], "no")

    def test_visible_section_enforces_required(self):
        schema = [
            {"type": "select", "id": "fuma", "label": "Fuma",
             "options": ["si", "no"]},
            {"type": "section", "label": "Detalle",
             "visible_when": {"field": "fuma", "equals": "si"},
             "fields": [
                 {"type": "number", "id": "cigs", "label": "Cigs",
                  "required": True}
             ]},
        ]
        _, errors = parse_post_to_answers(schema, _qd({"fuma": "si"}))
        self.assertTrue(any("Cigs" in e for e in errors))

    def test_number_min_max_emits_error(self):
        schema = [{"type": "number", "id": "edad", "label": "Edad",
                   "min": 0, "max": 120}]
        _, errors = parse_post_to_answers(schema, _qd({"edad": "150"}))
        self.assertTrue(any("≤ 120" in e for e in errors))

    def test_repeater_required_empty_emits_error(self):
        schema = [{
            "type": "repeater", "id": "meds", "label": "Medicamentos",
            "required": True,
            "fields": [{"type": "text", "id": "nombre", "label": "Nombre"}],
        }]
        _, errors = parse_post_to_answers(schema, _qd({}))
        self.assertTrue(any("Medicamentos" in e for e in errors))

    def test_repeater_parses_indexed_keys(self):
        schema = [{
            "type": "repeater", "id": "meds",
            "fields": [
                {"type": "text", "id": "nombre"},
                {"type": "number", "id": "dosis"},
            ],
        }]
        ans, errors = parse_post_to_answers(schema, _qd({
            "meds__0__nombre": "Ibuprofeno",
            "meds__0__dosis": "400",
            "meds__1__nombre": "Paracetamol",
            "meds__1__dosis": "500",
        }))
        self.assertEqual(errors, [])
        self.assertEqual(ans["meds"], [
            {"nombre": "Ibuprofeno", "dosis": 400},
            {"nombre": "Paracetamol", "dosis": 500},
        ])

    def test_repeater_orders_rows_numerically(self):
        """Si llegan filas con índices no contiguos (0 y 5), preserva orden."""
        schema = [{
            "type": "repeater", "id": "meds",
            "fields": [{"type": "text", "id": "nombre"}],
        }]
        ans, _ = parse_post_to_answers(schema, _qd({
            "meds__5__nombre": "B",
            "meds__0__nombre": "A",
        }))
        self.assertEqual(ans["meds"], [{"nombre": "A"}, {"nombre": "B"}])

    def test_multiselect_handles_multiple_values(self):
        schema = [{"type": "multiselect", "id": "tags", "label": "Tags"}]
        ans, _ = parse_post_to_answers(schema, _qd({"tags": ["a", "b", "c"]}))
        self.assertEqual(ans["tags"], ["a", "b", "c"])

    def test_validate_and_parse_post_integrates_computed(self):
        """IMC end-to-end: parsea ``peso``/``talla`` y devuelve ``computed``."""
        schema = [
            {"type": "number", "id": "peso_kg", "label": "Peso"},
            {"type": "number", "id": "talla_cm", "label": "Talla"},
            {"type": "computed", "id": "imc", "formula": "imc",
             "depends_on": ["peso_kg", "talla_cm"]},
        ]
        ans, computed, errors = validate_and_parse_post(
            schema, _qd({"peso_kg": "70", "talla_cm": "170"})
        )
        self.assertEqual(errors, [])
        self.assertEqual(ans, {"peso_kg": 70, "talla_cm": 170})
        self.assertEqual(computed, {"imc": 24.22})


# ---------------------------------------------------------------------------
# apply_computed (incl. IMC)
# ---------------------------------------------------------------------------


def _imc_node():
    return {
        "type": "computed", "id": "imc", "formula": "imc",
        "depends_on": ["peso_kg", "talla_cm"],
    }


class ApplyComputedTests(SimpleTestCase):
    def test_imc_normal(self):
        out = apply_computed([_imc_node()], {"peso_kg": 70, "talla_cm": 170})
        self.assertEqual(out, {"imc": 24.22})

    def test_imc_zero_talla_skipped(self):
        out = apply_computed([_imc_node()], {"peso_kg": 70, "talla_cm": 0})
        self.assertNotIn("imc", out)

    def test_imc_missing_dep_skipped(self):
        out = apply_computed([_imc_node()], {"peso_kg": 70})
        self.assertNotIn("imc", out)

    def test_imc_invalid_value_skipped(self):
        out = apply_computed([_imc_node()],
                             {"peso_kg": "abc", "talla_cm": 170})
        self.assertNotIn("imc", out)

    def test_imc_uses_default_dep_names_when_missing(self):
        """Cuando ``depends_on`` está vacío, usa ``peso_kg``/``talla_cm`` por defecto."""
        node = {"type": "computed", "id": "imc", "formula": "imc"}
        out = apply_computed([node], {"peso_kg": 60, "talla_cm": 160})
        self.assertAlmostEqual(out["imc"], 23.44, places=2)

    def test_generic_formula_with_precision(self):
        node = {"type": "computed", "id": "total", "formula": "a+b",
                "depends_on": ["a", "b"], "precision": 2}
        out = apply_computed([node], {"a": 1.111, "b": 2.111})
        self.assertEqual(out["total"], 3.22)

    def test_generic_formula_division(self):
        node = {"type": "computed", "id": "ratio", "formula": "a/b",
                "depends_on": ["a", "b"], "precision": 2}
        out = apply_computed([node], {"a": 8, "b": 10})
        self.assertEqual(out["ratio"], 0.8)

    def test_generic_formula_division_by_zero_skipped(self):
        node = {"type": "computed", "id": "ratio", "formula": "a/b",
                "depends_on": ["a", "b"]}
        out = apply_computed([node], {"a": 8, "b": 0})
        self.assertNotIn("ratio", out)

    def test_generic_formula_dep_non_numeric_skipped(self):
        node = {"type": "computed", "id": "x", "formula": "a+b",
                "depends_on": ["a", "b"]}
        out = apply_computed([node], {"a": 1, "b": "hola"})
        self.assertNotIn("x", out)

    def test_generic_formula_missing_dep_skipped(self):
        node = {"type": "computed", "id": "x", "formula": "a+b",
                "depends_on": ["a", "b"]}
        out = apply_computed([node], {"a": 1})
        self.assertNotIn("x", out)

    def test_walks_into_sections(self):
        schema = [{
            "type": "section", "label": "S",
            "fields": [_imc_node()],
        }]
        out = apply_computed(schema, {"peso_kg": 60, "talla_cm": 160})
        self.assertAlmostEqual(out["imc"], 23.44, places=2)

    def test_precision_invalid_falls_back_to_unrounded(self):
        node = {"type": "computed", "id": "x", "formula": "a+b",
                "depends_on": ["a", "b"], "precision": "abc"}
        out = apply_computed([node], {"a": 1.123, "b": 2})
        self.assertAlmostEqual(out["x"], 3.123, places=3)

    def test_empty_formula_skipped(self):
        node = {"type": "computed", "id": "x", "formula": "   ",
                "depends_on": ["a"]}
        out = apply_computed([node], {"a": 1})
        self.assertNotIn("x", out)


# ---------------------------------------------------------------------------
# _safe_eval_arithmetic — núcleo del sandbox de fórmulas
# ---------------------------------------------------------------------------


class SafeEvalArithmeticTests(SimpleTestCase):
    """Pruebas básicas + de edge-case. Los tests de seguridad/inyección viven
    en ``test_form_builder_security``."""

    def test_basic_arithmetic(self):
        self.assertEqual(_safe_eval_arithmetic("a+b", {"a": 1, "b": 2}), 3.0)

    def test_complex_expression(self):
        self.assertAlmostEqual(
            _safe_eval_arithmetic("base*(1+iva)", {"base": 100, "iva": 0.19}),
            119.0, places=2,
        )

    def test_rejects_unknown_name(self):
        # "c" no está en names -> None
        self.assertIsNone(
            _safe_eval_arithmetic("a+c", {"a": 1, "b": 2})
        )

    def test_syntax_error_returns_none(self):
        self.assertIsNone(_safe_eval_arithmetic("a+", {"a": 1}))

    def test_division_by_zero_returns_none(self):
        self.assertIsNone(_safe_eval_arithmetic("a/b", {"a": 1, "b": 0}))

    def test_empty_formula_returns_none(self):
        self.assertIsNone(_safe_eval_arithmetic("", {}))
        self.assertIsNone(_safe_eval_arithmetic("   ", {}))
