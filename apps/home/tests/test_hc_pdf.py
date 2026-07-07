# -*- encoding: utf-8 -*-
"""Smoke test generación PDF WeasyPrint / fallback ReportLab."""
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase

from apps.home.models import DatosDemograficos, Proyecto, TipoVisita, Visita
from apps.home.views.pdf import construir_pdf_visita


def _paciente():
    return DatosDemograficos.objects.create(
        primer_nombre="PDF",
        primer_apellido="Smoke",
        numero_documento="PDF-SMOKE-1",
        fecha_nacimiento="1990-01-01",
        edad=35,
        celular="3009998877",
    )


class HCPDFSmokeTests(TestCase):
    def test_construir_pdf_visita_genera_bytes(self):
        proyecto = Proyecto.objects.create(nombre="PDF Smoke")
        tipo = TipoVisita.objects.create(nombre="Control", proyecto=proyecto)
        paciente = _paciente()
        visita = Visita.objects.create(
            nombre="V-PDF",
            paciente=paciente,
            Tipo_visita=tipo,
            notas_aclaratorias="Nota de prueba",
        )
        buf = BytesIO()
        construir_pdf_visita(buf, visita)
        content = buf.getvalue()
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 100)
