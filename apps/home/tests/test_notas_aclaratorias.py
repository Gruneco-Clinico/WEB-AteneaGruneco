# -*- encoding: utf-8 -*-
"""
Tests for notas_aclaratorias field on Visita model.

Covers:
- Field existence and defaults
- Editable after visit is signed (firmado=True)
- Appears in PDF output
- View requires authentication
"""
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User
from io import BytesIO

from apps.home.models import Visita, DatosDemograficos, TipoVisita, Proyecto

from django.urls import reverse


def _make_paciente(suffix="1"):
    """Helper: create DatosDemograficos with all required non-nullable fields."""
    return DatosDemograficos.objects.create(
        primer_nombre=f"Test{suffix}",
        primer_apellido=f"Apellido{suffix}",
        numero_documento=f"DOC{suffix}",
        fecha_nacimiento="1985-06-15",
        edad=40,
        celular=f"300000{suffix}",
    )


class NotasAclaratoriasModelTests(TestCase):
    """Model-level tests for the notas_aclaratorias field."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("testuser", password="pass1234")
        cls.proyecto = Proyecto.objects.create(nombre="TestProyecto")
        cls.tipo = TipoVisita.objects.create(
            nombre="Control",
            proyecto=cls.proyecto,
            examenes=[],
        )
        cls.paciente = _make_paciente("model1")

    def test_field_exists_and_defaults_to_none(self):
        """notas_aclaratorias exists and default is None."""
        visita = Visita.objects.create(
            nombre="V1", paciente=self.paciente, Tipo_visita=self.tipo,
        )
        self.assertIsNone(visita.notas_aclaratorias)

    def test_save_notas_on_open_visit(self):
        """Can set notas on an open (unfirmed) visit."""
        visita = Visita.objects.create(
            nombre="V2", paciente=self.paciente, Tipo_visita=self.tipo,
        )
        visita.notas_aclaratorias = "Paciente reportó dolor de cabeza post-evaluación."
        visita.save()
        visita.refresh_from_db()
        self.assertEqual(
            visita.notas_aclaratorias,
            "Paciente reportó dolor de cabeza post-evaluación.",
        )

    def test_save_notas_on_signed_visit(self):
        """notas_aclaratorias CAN be edited even when firmado=True."""
        visita = Visita.objects.create(
            nombre="V3",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
            firmado=True,
            firmado_por=self.user,
            estado_visita="cerrada",
        )
        visita.notas_aclaratorias = "Corrección: dosis indicada era 50mg, no 500mg."
        visita.save()
        visita.refresh_from_db()
        self.assertEqual(
            visita.notas_aclaratorias,
            "Corrección: dosis indicada era 50mg, no 500mg.",
        )

    def test_blank_notas_allowed(self):
        """Empty string is valid."""
        visita = Visita.objects.create(
            nombre="V4", paciente=self.paciente, Tipo_visita=self.tipo,
            notas_aclaratorias="",
        )
        visita.refresh_from_db()
        self.assertEqual(visita.notas_aclaratorias, "")


class NotasAclaratoriasPDFTests(TestCase):
    """Verify notas_aclaratorias renders inside the PDF."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("pdfuser", password="pass1234")
        cls.proyecto = Proyecto.objects.create(nombre="PDFProyecto")
        cls.tipo = TipoVisita.objects.create(
            nombre="Seguimiento",
            proyecto=cls.proyecto,
            examenes=[],
        )
        cls.paciente = _make_paciente("pdf1")

    def test_pdf_contains_notas_aclaratorias(self):
        """When notas_aclaratorias is set, the PDF should be larger (section added)."""
        from apps.home.views.pdf import construir_pdf_visita

        # PDF without notas
        visita_sin = Visita.objects.create(
            nombre="VisitaSin",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
            firmado=True,
            firmado_por=self.user,
        )
        buf_sin = BytesIO()
        construir_pdf_visita(buf_sin, visita_sin)
        size_sin = len(buf_sin.getvalue())

        # PDF with notas
        visita_con = Visita.objects.create(
            nombre="VisitaCon",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
            firmado=True,
            firmado_por=self.user,
            notas_aclaratorias="NOTA-PRUEBA: Se ajustó la interpretación del MoCA.",
        )
        buf_con = BytesIO()
        construir_pdf_visita(buf_con, visita_con)
        size_con = len(buf_con.getvalue())

        # The PDF with notas should be meaningfully larger
        self.assertGreater(size_con, size_sin)

    def test_pdf_without_notas_does_not_crash(self):
        """PDF generation works fine when notas_aclaratorias is None."""
        from apps.home.views.pdf import construir_pdf_visita

        visita = Visita.objects.create(
            nombre="VisitaSinNotas",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
        )
        buf = BytesIO()
        construir_pdf_visita(buf, visita)
        self.assertGreater(len(buf.getvalue()), 100)


@override_settings(SECURE_SSL_REDIRECT=False)
class NotasAclaratoriasViewTests(TestCase):
    """Test the editar_notas_aclaratorias view."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("viewuser", password="pass1234")
        cls.proyecto = Proyecto.objects.create(nombre="ViewProyecto")
        cls.tipo = TipoVisita.objects.create(
            nombre="Inicial",
            proyecto=cls.proyecto,
            examenes=[],
        )
        cls.paciente = _make_paciente("view1")

    def test_requires_login(self):
        """Anonymous users are redirected to login."""
        visita = Visita.objects.create(
            nombre="V-Auth", paciente=self.paciente, Tipo_visita=self.tipo,
        )
        url = reverse("editar_notas_aclaratorias", args=[visita.id])
        resp = self.client.post(url, {"notas_aclaratorias": "test"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_post_saves_notas(self):
        """Authenticated POST updates notas_aclaratorias."""
        visita = Visita.objects.create(
            nombre="V-Save",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
            firmado=True,
            firmado_por=self.user,
        )
        self.client.login(username="viewuser", password="pass1234")
        url = reverse("editar_notas_aclaratorias", args=[visita.id])
        resp = self.client.post(url, {"notas_aclaratorias": "Nueva nota aclaratoria."})
        self.assertEqual(resp.status_code, 302)
        visita.refresh_from_db()
        self.assertEqual(visita.notas_aclaratorias, "Nueva nota aclaratoria.")

    def test_get_not_allowed(self):
        """GET method should redirect (only POST is accepted)."""
        visita = Visita.objects.create(
            nombre="V-Get", paciente=self.paciente, Tipo_visita=self.tipo,
        )
        self.client.login(username="viewuser", password="pass1234")
        url = reverse("editar_notas_aclaratorias", args=[visita.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
