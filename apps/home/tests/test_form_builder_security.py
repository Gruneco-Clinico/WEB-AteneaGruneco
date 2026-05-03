# -*- encoding: utf-8 -*-
"""
Tests de seguridad del sandbox de fórmulas (``_safe_eval_arithmetic``).

El módulo permite que un usuario *staff* defina la fórmula de un campo
``computed`` desde el editor visual. El valor se almacena en
``Examen.campos`` (JSONField) y se ejecuta con ``eval`` en
``apps/home/form_builder/schema.py``. Esta superficie es **el riesgo de
seguridad #1 del módulo**: si el sandbox falla, un staff comprometido
podría ejecutar código arbitrario con privilegios del worker Django.

Estos tests verifican que ``_safe_eval_arithmetic`` rechace todos los
vectores de inyección conocidos.
"""

from django.test import SimpleTestCase

from apps.home.form_builder.schema import _safe_eval_arithmetic, apply_computed


class FormulaSandboxInjectionTests(SimpleTestCase):
    def test_rejects_dunder_import(self):
        # __import__ aparece en co_names; no está en allowed -> None
        formula = '__import__("os").system("ls")'
        self.assertIsNone(_safe_eval_arithmetic(formula, {}))

    def test_rejects_unknown_attribute_access(self):
        # ``system`` aparece como nombre y no está en names -> None
        self.assertIsNone(_safe_eval_arithmetic("os.system", {"os": 1}))

    def test_rejects_open_builtin(self):
        self.assertIsNone(
            _safe_eval_arithmetic('open("/etc/passwd").read()', {})
        )

    def test_rejects_eval_in_formula(self):
        self.assertIsNone(_safe_eval_arithmetic('eval("1+1")', {}))

    def test_rejects_exec_in_formula(self):
        self.assertIsNone(_safe_eval_arithmetic('exec("x=1")', {}))

    def test_rejects_getattr_dunder(self):
        # Vector clásico: acceder a ``__class__`` y bajar la jerarquía.
        formula = "().__class__.__bases__[0].__subclasses__()"
        self.assertIsNone(_safe_eval_arithmetic(formula, {}))

    def test_rejects_globals(self):
        self.assertIsNone(_safe_eval_arithmetic("globals()", {}))

    def test_rejects_locals(self):
        self.assertIsNone(_safe_eval_arithmetic("locals()", {}))

    def test_rejects_compile(self):
        self.assertIsNone(
            _safe_eval_arithmetic('compile("1", "<x>", "eval")', {})
        )

    def test_rejects_help(self):
        self.assertIsNone(_safe_eval_arithmetic("help", {}))

    def test_rejects_print(self):
        # ``print`` no está en names -> rechazado.
        self.assertIsNone(_safe_eval_arithmetic('print("x")', {}))

    def test_rejects_extra_name_outside_allowlist(self):
        # Con ``a`` permitido y ``c`` no permitido, debe rechazar.
        self.assertIsNone(_safe_eval_arithmetic("a + c", {"a": 1}))

    def test_rejects_chained_attribute_walk(self):
        formula = '"".__class__.__mro__[1].__subclasses__()'
        self.assertIsNone(_safe_eval_arithmetic(formula, {}))

    def test_rejects_lambda_eval(self):
        # Aunque sea sintácticamente válido, las llamadas a builtins fallarán
        # por __builtins__={} y los nombres no están en allowed.
        self.assertIsNone(
            _safe_eval_arithmetic('(lambda: __import__("os"))()', {})
        )

    def test_allows_only_whitelisted_names(self):
        # Caso positivo: cuando todo está permitido, evalúa correctamente.
        self.assertEqual(
            _safe_eval_arithmetic("a + b", {"a": 2, "b": 3}), 5.0
        )

    def test_apply_computed_does_not_execute_malicious_formula(self):
        """Un esquema malicioso publicado no debe ejecutar código."""
        schema = [{
            "type": "computed", "id": "evil",
            "formula": '__import__("os").system("echo PWNED")',
            "depends_on": ["a"],
        }]
        out = apply_computed(schema, {"a": 1})
        # No debe haber valor calculado y no debe haber raise.
        self.assertNotIn("evil", out)


class FormulaSandboxBoundaryTests(SimpleTestCase):
    """Casos en la frontera entre lo permitido y lo no permitido."""

    def test_unicode_identifier_outside_allowlist_rejected(self):
        # Identificador Unicode válido pero no permitido.
        self.assertIsNone(_safe_eval_arithmetic("álpha + 1", {"a": 1}))

    def test_very_long_formula_rejected_if_unknown_names(self):
        formula = " + ".join(["x{}".format(i) for i in range(50)])
        self.assertIsNone(_safe_eval_arithmetic(formula, {"x0": 1}))

    def test_bitwise_ops_with_allowed_names(self):
        # Operadores bit-a-bit son legítimos para campos puntaje/flags.
        self.assertEqual(_safe_eval_arithmetic("a | b", {"a": 5, "b": 2}), 7.0)

    def test_power_operator_with_allowed_names(self):
        self.assertEqual(_safe_eval_arithmetic("a ** b", {"a": 2, "b": 3}), 8.0)

    def test_unary_minus(self):
        self.assertEqual(_safe_eval_arithmetic("-a", {"a": 5}), -5.0)
