# -*- encoding: utf-8 -*-
"""Test para el campo de consentimiento informado en Proyecto"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.home.models import Proyecto


class ConsentimientoPDFTest(TestCase):
    def test_proyecto_puede_tener_consentimiento_pdf(self):
        """Verificar que se puede crear un proyecto con PDF de consentimiento"""
        # Crear un archivo PDF simulado
        pdf_content = b'%PDF-1.4 fake pdf content'
        pdf_file = SimpleUploadedFile(
            "consentimiento_test.pdf",
            pdf_content,
            content_type="application/pdf"
        )
        
        # Crear proyecto con consentimiento
        proyecto = Proyecto.objects.create(
            nombre="Proyecto Test Consentimiento",
            descripcion="Proyecto de prueba",
            consentimiento_pdf=pdf_file
        )
        
        # Verificar que se guardó correctamente
        self.assertTrue(proyecto.consentimiento_pdf)
        self.assertIn('consentimientos/', proyecto.consentimiento_pdf.name)
        
    def test_proyecto_sin_consentimiento_es_valido(self):
        """Verificar que un proyecto sin consentimiento es válido (campo opcional)"""
        proyecto = Proyecto.objects.create(
            nombre="Proyecto Sin Consentimiento",
            descripcion="Proyecto de prueba sin PDF"
        )
        
        self.assertFalse(proyecto.consentimiento_pdf)
        self.assertEqual(proyecto.nombre, "Proyecto Sin Consentimiento")
