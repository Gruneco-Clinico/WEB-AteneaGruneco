# -*- encoding: utf-8 -*-
"""
Tests for audit trail (django-simple-history) on clinical models.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

from apps.home.models import DatosDemograficos, Visita, VisitaExamen


class DatosDemograficosHistoryTests(TestCase):
    """Verify that DatosDemograficos tracks creation and updates."""

    def setUp(self):
        self.paciente = DatosDemograficos.objects.create(
            primer_nombre="Juan",
            primer_apellido="Pérez",
            numero_documento="1234567890",
            fecha_nacimiento="1980-01-01",
            edad=46,
            celular="3001234567",
            correo="juan@test.com",
            ocupacion="Ingeniero",
            religion="Católico",
            eps="Sura",
        )

    def test_creation_generates_history_record(self):
        self.assertEqual(self.paciente.history.count(), 1)
        record = self.paciente.history.first()
        self.assertEqual(record.history_type, "+")
        self.assertEqual(record.primer_nombre, "Juan")

    def test_update_generates_history_record(self):
        self.paciente.primer_nombre = "Carlos"
        self.paciente.save()
        self.assertEqual(self.paciente.history.count(), 2)
        latest = self.paciente.history.first()
        self.assertEqual(latest.history_type, "~")
        self.assertEqual(latest.primer_nombre, "Carlos")

    def test_delete_generates_history_record(self):
        pk = self.paciente.pk
        self.paciente.delete()
        history = DatosDemograficos.history.filter(id=pk)
        self.assertEqual(history.count(), 2)  # create + delete
        self.assertEqual(history.first().history_type, "-")


class VisitaHistoryTests(TestCase):
    """Verify that Visita tracks creation and updates."""

    def setUp(self):
        self.paciente = DatosDemograficos.objects.create(
            primer_nombre="Ana",
            primer_apellido="López",
            numero_documento="9876543210",
            fecha_nacimiento="1990-05-15",
            edad=35,
            celular="3009876543",
            correo="ana@test.com",
            ocupacion="Médico",
            religion="Ninguna",
            eps="Nueva EPS",
        )
        self.visita = Visita.objects.create(
            paciente=self.paciente,
            nombre="Visita Inicial",
        )

    def test_creation_generates_history_record(self):
        self.assertEqual(self.visita.history.count(), 1)
        record = self.visita.history.first()
        self.assertEqual(record.history_type, "+")

    def test_update_firmado_generates_history_record(self):
        self.visita.firmado = True
        self.visita.save()
        self.assertEqual(self.visita.history.count(), 2)
        latest = self.visita.history.first()
        self.assertEqual(latest.history_type, "~")
        self.assertTrue(latest.firmado)


class VisitaExamenHistoryTests(TestCase):
    """Verify that VisitaExamen tracks state changes."""

    def setUp(self):
        from apps.home.models import Examen

        self.paciente = DatosDemograficos.objects.create(
            primer_nombre="Pedro",
            primer_apellido="García",
            numero_documento="5555555555",
            fecha_nacimiento="1975-03-20",
            edad=50,
            celular="3005555555",
            correo="pedro@test.com",
            ocupacion="Profesor",
            religion="Cristiano",
            eps="Sanitas",
        )
        self.visita = Visita.objects.create(
            paciente=self.paciente,
            nombre="Visita Control",
        )
        self.examen = Examen.objects.create(
            nombre="Epworth Test",
            descripcion="Test de somnolencia",
        )
        self.ve = VisitaExamen.objects.create(
            visita=self.visita,
            examen=self.examen,
            estado="pendiente",
        )

    def test_creation_generates_history_record(self):
        self.assertEqual(self.ve.history.count(), 1)

    def test_estado_change_generates_history_record(self):
        self.ve.estado = "completado"
        self.ve.save()
        self.assertEqual(self.ve.history.count(), 2)
        latest = self.ve.history.first()
        self.assertEqual(latest.estado, "completado")
