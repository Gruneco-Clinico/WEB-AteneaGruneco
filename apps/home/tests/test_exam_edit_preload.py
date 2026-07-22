# -*- encoding: utf-8 -*-
"""Tests B-11: precarga de datos al editar exámenes legacy."""
from django.contrib.auth.models import User
from django.test import TestCase

from apps.home.exam_registry import get_exam_model
from apps.home.models import (
    AntecedenteAlergico,
    AntecedenteEpidemiologico,
    AntecedentePatologico,
    AntecedenteToxico,
    AntecedenteTraumatico,
    AntecedentesResult,
    AntecedentesVisitaLink,
    DatosDemograficos,
    Examen,
    ExamenFisicoResult,
    ExamenNeurologicoResult,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
)
from apps.home.services.exam_edit_context import build_datos_examen_edicion


class ExamEditPreloadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("tester", password="x")
        self.proyecto = Proyecto.objects.create(nombre="Test Proyecto")
        self.tipo = TipoVisita.objects.create(
            nombre="Visita test", proyecto=self.proyecto
        )
        self.paciente = DatosDemograficos.objects.create(
            primer_nombre="Ana",
            primer_apellido="Prueba",
            numero_documento="100",
            fecha_nacimiento="1985-06-15",
            edad=40,
            celular="300000100",
        )
        self.visita = Visita.objects.create(
            paciente=self.paciente,
            Tipo_visita=self.tipo,
            nombre="V1",
        )

    def _ve(self, examen_id, nombre):
        examen, _ = Examen.objects.get_or_create(
            id=examen_id, defaults={"nombre": nombre}
        )
        if examen.nombre != nombre:
            examen.nombre = nombre
            examen.save(update_fields=["nombre"])
        return VisitaExamen.objects.create(
            visita=self.visita,
            examen=examen,
            estado="completado",
        )

    def test_neurologico_preload_booleans(self):
        ve = self._ve(9, "General_ExamenNeurológico")
        ExamenNeurologicoResult.objects.create(
            visita_examen=ve,
            clavos_izquierdo=True,
            cafe_derecho=True,
            amaurosis=False,
        )
        model = get_exam_model(9)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 9, model)
        self.assertTrue(modo)
        self.assertTrue(datos["clavos_izquierdo"])
        self.assertTrue(datos["cafe_derecho"])
        self.assertFalse(datos["amaurosis"])

    def test_fisico_preload_pared_masas_megalias(self):
        ve = self._ve(3, "General_ExamenFísico")
        ExamenFisicoResult.objects.create(
            visita_examen=ve,
            talla=170,
            peso=70,
            temperatura=36.5,
            frecuencia_cardiaca=72,
            frecuencia_respiratoria=16,
            presion_arterial_sistolica=120,
            presion_arterial_diastolica=80,
            pared_abdominal_normal=False,
            pared_abdominal_anormal=True,
            masas=True,
            megalias=False,
        )
        model = get_exam_model(3)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 3, model)
        self.assertTrue(modo)
        self.assertFalse(datos["pared_abdominal_normal"])
        self.assertTrue(datos["pared_abdominal_anormal"])
        self.assertTrue(datos["masas"])
        self.assertFalse(datos["megalias"])

    def test_antecedentes_preload_includes_children(self):
        ve = self._ve(5, "General_Antecedentes")
        ant = AntecedentesResult.objects.create(paciente=self.paciente)
        AntecedentesVisitaLink.objects.create(
            visita_examen=ve, antecedentes_result=ant
        )
        AntecedentePatologico.objects.create(
            antecedente_result=ant,
            tipo_patologia="Hipertensión",
            fecha_inicio="2015-01-01",
            ha_recibido_tratamiento=True,
            detalle_tratamiento="Losartán",
            tiene_complicaciones=False,
            activo=True,
            observaciones="Controlado",
        )
        model = get_exam_model(5)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 5, model)
        self.assertTrue(modo)
        self.assertEqual(len(datos["patologicos"]), 1)
        row = datos["patologicos"][0]
        self.assertTrue(row["ha_recibido_tratamiento"])
        self.assertEqual(row["detalle_tratamiento"], "Losartán")
        self.assertEqual(row["observaciones"], "Controlado")

    def test_antecedentes_preload_toxicos_alergicos_traumaticos_epi(self):
        ve = self._ve(5, "General_Antecedentes")
        ant = AntecedentesResult.objects.create(paciente=self.paciente)
        AntecedentesVisitaLink.objects.create(
            visita_examen=ve, antecedentes_result=ant
        )
        AntecedenteToxico.objects.create(
            antecedente_result=ant,
            tipos_toxico=["tabaquismo", "alcohol"],
            fecha_inicio="2020-01-01",
            observaciones="Exfumador",
        )
        AntecedenteAlergico.objects.create(
            antecedente_result=ant,
            descripcion="Penicilina",
            fecha_inicio="2019-05-01",
            observaciones="Urticaria",
        )
        AntecedenteTraumatico.objects.create(
            antecedente_result=ant,
            descripcion="Fractura tibia",
            fecha_inicio="2018-03-15",
            activo=False,
        )
        AntecedenteEpidemiologico.objects.create(
            antecedente_result=ant,
            tipo_antecedente="COVID-19",
            fecha_inicio="2021-06-01",
            activo_actualmente=False,
            observaciones="Leve",
        )
        model = get_exam_model(5)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 5, model)
        self.assertTrue(modo)
        self.assertEqual(datos["toxicos"][0]["tipos_toxico"], ["tabaquismo", "alcohol"])
        self.assertEqual(datos["alergicos"][0]["descripcion"], "Penicilina")
        self.assertEqual(datos["traumaticos"][0]["descripcion"], "Fractura tibia")
        self.assertEqual(datos["epidemiologicos"][0]["tipo_antecedente"], "COVID-19")
        self.assertEqual(datos["epidemiologicos"][0]["descripcion"], "COVID-19")
        self.assertEqual(datos["epidemiologicos"][0]["observaciones"], "Leve")
