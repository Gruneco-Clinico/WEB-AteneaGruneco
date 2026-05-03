# -*- encoding: utf-8 -*-
"""
Tests de los templatetags / filtros del Form Builder.
"""

import html
import json

from django.test import SimpleTestCase

from apps.home.templatetags.form_builder_tags import (
    contains_val,
    fb_attr_json,
    fb_concat,
    fb_filter_non_sections,
    fb_filter_sections,
    fb_input_name,
    get_item,
)


class GetItemTests(SimpleTestCase):
    def test_dict_lookup(self):
        self.assertEqual(get_item({"a": 1}, "a"), 1)

    def test_missing_returns_none(self):
        self.assertIsNone(get_item({"a": 1}, "b"))

    def test_none_dict_returns_none(self):
        self.assertIsNone(get_item(None, "a"))

    def test_non_dict_returns_none(self):
        self.assertIsNone(get_item("string", "a"))


class ContainsValTests(SimpleTestCase):
    def test_value_in_list(self):
        self.assertTrue(contains_val(["a", "b"], "a"))

    def test_value_not_in_list(self):
        self.assertFalse(contains_val(["a", "b"], "c"))

    def test_empty_returns_false(self):
        self.assertFalse(contains_val(None, "x"))
        self.assertFalse(contains_val([], "x"))

    def test_scalar_compare(self):
        self.assertTrue(contains_val("abc", "abc"))
        self.assertFalse(contains_val("abc", "def"))

    def test_int_str_coercion(self):
        self.assertTrue(contains_val(["1", "2"], 1))


class FbInputNameTests(SimpleTestCase):
    def test_with_prefix(self):
        self.assertEqual(fb_input_name("meds__0__", "nombre"),
                         "meds__0__nombre")

    def test_without_prefix(self):
        self.assertEqual(fb_input_name("", "nombre"), "nombre")
        self.assertEqual(fb_input_name(None, "nombre"), "nombre")


class FbConcatTests(SimpleTestCase):
    def test_concat_str(self):
        self.assertEqual(fb_concat("a", "b", "c"), "abc")

    def test_concat_mixed(self):
        self.assertEqual(fb_concat("v", 1, "_x"), "v1_x")


class FbAttrJsonTests(SimpleTestCase):
    def test_serializes_dict(self):
        # ``fb_attr_json`` aplica HTML-escape sobre el JSON para que el
        # resultado sea seguro dentro de un atributo HTML; deshacemos el
        # escape antes de parsear.
        out = fb_attr_json({"field": "x", "equals": "y"})
        self.assertEqual(
            json.loads(html.unescape(out)),
            {"field": "x", "equals": "y"},
        )

    def test_escapes_html(self):
        out = fb_attr_json({"x": "<script>"})
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;", out)
        self.assertIn("&gt;", out)

    def test_none_returns_empty_string(self):
        self.assertEqual(fb_attr_json(None), "")


class FbFilterSectionsTests(SimpleTestCase):
    SCHEMA = [
        {"type": "section", "label": "S1"},
        {"type": "text", "id": "a"},
        {"type": "section", "label": "S2"},
        {"type": "number", "id": "b"},
    ]

    def test_filter_sections_returns_only_sections(self):
        out = fb_filter_sections(self.SCHEMA)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(s["type"] == "section" for s in out))

    def test_filter_non_sections_excludes_sections(self):
        out = fb_filter_non_sections(self.SCHEMA)
        self.assertEqual(len(out), 2)
        self.assertTrue(all(s["type"] != "section" for s in out))

    def test_empty_input(self):
        self.assertEqual(fb_filter_sections(None), [])
        self.assertEqual(fb_filter_non_sections([]), [])

    def test_works_with_objects_having_type_attr(self):
        class Node:
            def __init__(self, t):
                self.type = t

        nodes = [Node("section"), Node("text")]
        self.assertEqual(len(fb_filter_sections(nodes)), 1)
        self.assertEqual(len(fb_filter_non_sections(nodes)), 1)
