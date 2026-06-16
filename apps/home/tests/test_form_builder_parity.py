# -*- encoding: utf-8 -*-
"""
Tests de paridad entre backend (``schema.visible_when_match``) y frontend
(``runtime.evalVisible``).

La condición ``visible_when`` se evalúa **dos veces** en el sistema:
- En Python al guardar (``schema.parse_post_to_answers`` decide qué validar).
- En JS en el navegador (``runtime.evalVisible`` muestra/oculta wraps).

Si ambas implementaciones divergen, el usuario verá un campo, lo dejará
vacío y el backend lo marcará como obligatorio (o viceversa). Por eso
ambas se prueban contra **la misma tabla de casos**:

  ``tests/fixtures/visible_when_cases.json``

El test JS equivalente vive en ``tests/js/parity.spec.js``.
"""

import json
import os

from django.test import SimpleTestCase

from apps.home.form_builder.schema import visible_when_match


FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "tests", "fixtures", "visible_when_cases.json",
)


class VisibleWhenParityTests(SimpleTestCase):
    """Recorre la tabla compartida y verifica el resultado en backend."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(FIXTURE_PATH, encoding="utf-8") as f:
            cls.cases = json.load(f)

    def test_each_case(self):
        for case in self.cases:
            with self.subTest(case=case["name"]):
                node = (
                    {"visible_when": case["cond"]}
                    if case["cond"] is not None
                    else {}
                )
                result = visible_when_match(node, case["answers"])
                self.assertEqual(
                    result, case["expected"],
                    msg=(f"caso {case['name']!r}: backend devolvió {result}, "
                         f"esperado {case['expected']}"),
                )
