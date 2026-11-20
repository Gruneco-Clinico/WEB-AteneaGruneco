# -*- encoding: utf-8 -*-
"""Verifica que todas las plantillas bajo apps/templates/ compilen sin errores de sintaxis."""
from pathlib import Path

from django.conf import settings
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import get_template
from django.test import SimpleTestCase

TEMPLATES_ROOT = Path(settings.TEMPLATE_DIR)


class TemplatesCompilanTests(SimpleTestCase):
    def test_todas_las_plantillas_compilan(self):
        rutas = sorted(TEMPLATES_ROOT.rglob("*.html"))
        self.assertTrue(rutas, f"No se encontraron plantillas en {TEMPLATES_ROOT}")

        fallos = []
        for ruta in rutas:
            relativa = ruta.relative_to(TEMPLATES_ROOT).as_posix()
            try:
                get_template(relativa)
            except TemplateSyntaxError as exc:
                fallos.append(f"{relativa}: TemplateSyntaxError: {exc}")
            except TemplateDoesNotExist as exc:
                fallos.append(f"{relativa}: TemplateDoesNotExist: {exc}")
            except Exception as exc:  # noqa: BLE001 - se acumula cualquier error de carga
                fallos.append(f"{relativa}: {type(exc).__name__}: {exc}")

        if fallos:
            self.fail(
                f"{len(fallos)} plantilla(s) no compilan:\n" + "\n".join(fallos)
            )
