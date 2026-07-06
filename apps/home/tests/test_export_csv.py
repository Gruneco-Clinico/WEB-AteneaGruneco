# -*- encoding: utf-8 -*-
"""Tests exportación CSV con export_registry."""
from django.test import TestCase

from apps.home.models import (
    DatosDemograficos,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
    Examen,
    PittsburghResult,
    PuntajeCDRResult,
)
from apps.home.export_registry import extract_exam_export_data
import json


def _paciente():
    return DatosDemograficos.objects.create(
        primer_nombre="Export",
        primer_apellido="Test",
        numero_documento="EXP-CSV-1",
        fecha_nacimiento="1988-03-10",
        edad=37,
        celular="3001112233",
    )


class ExportRegistryTests(TestCase):
    def test_pittsburgh_puntuacion_total_alias(self):
        proyecto = Proyecto.objects.create(nombre="Sueño Export")
        tipo = TipoVisita.objects.create(nombre="Inicial", proyecto=proyecto)
        paciente = _paciente()
        examen = Examen.objects.create(id=13, nombre="Pittsburgh", categoria="SUENO")
        visita = Visita.objects.create(
            nombre="V1", paciente=paciente, Tipo_visita=tipo
        )
        ve = VisitaExamen.objects.create(
            visita=visita, examen=examen, estado="completado"
        )
        PittsburghResult.objects.create(
            visita_examen=ve,
            puntuacion_total=12,
            interpretacion="Buen dormidor",
        )
        datos = extract_exam_export_data(ve, campos_solicitados=["puntaje_total"])
        self.assertEqual(datos.get("puntaje_total"), 12)

    def test_cdr_resultados_tabla_json(self):
        proyecto = Proyecto.objects.create(nombre="Anosognosia Export")
        tipo = TipoVisita.objects.create(nombre="Eval", proyecto=proyecto)
        paciente = _paciente()
        examen = Examen.objects.create(
            id=35, nombre="CDR_Evaluacion_Clinica_ANG", categoria="ANOSOGNOSIA"
        )
        visita = Visita.objects.create(
            nombre="V1", paciente=paciente, Tipo_visita=tipo
        )
        ve = VisitaExamen.objects.create(
            visita=visita, examen=examen, estado="completado"
        )
        PuntajeCDRResult.objects.create(
            visita_examen=ve,
            cdr_memoria="0.5",
            cdr_orientacion="1",
            cdr_juicio="1",
            cdr_comunitarias="1",
            cdr_pasatiempos="1",
            cdr_cuidado="2",
            cdr_global="1",
            cdr_interpretacion="Demencia leve",
        )
        datos = extract_exam_export_data(ve, campos_solicitados=["resultados_tabla"])
        filas = json.loads(datos["resultados_tabla"])
        self.assertGreaterEqual(len(filas), 7)
        self.assertEqual(filas[0]["parametro"], "CDR Memoria")
        self.assertEqual(filas[0]["resultado"], "0.5")
        interpretaciones = [f for f in filas if "Interpretación" in f["parametro"]]
        self.assertEqual(len(interpretaciones), 1)
        self.assertEqual(interpretaciones[0]["resultado"], "Demencia leve")

    def test_anamnesis_cuidador_resultados_tabla_json(self):
        proyecto = Proyecto.objects.create(nombre="Anosognosia Export")
        tipo = TipoVisita.objects.create(nombre="Eval", proyecto=proyecto)
        paciente = _paciente()
        examen = Examen.objects.create(
            id=38, nombre="Anamnesis_Cuidador_ANG", categoria="ANOSOGNOSIA"
        )
        visita = Visita.objects.create(
            nombre="V1", paciente=paciente, Tipo_visita=tipo
        )
        ve = VisitaExamen.objects.create(
            visita=visita, examen=examen, estado="completado"
        )
        from apps.home.models import AnamnesisCuidadorResult

        AnamnesisCuidadorResult.objects.create(
            visita_examen=ve,
            nombres_apellidos="Blanca Arango Arango",
            documento="cc 42886117",
            lugar_nacimiento="Medellín",
            lugar_procedencia="Medellín",
            edad=67,
            sexo="Femenino",
            estado_civil="Soltero",
            relacion="Hija",
            tiempo_acompanando="2021",
            ingresos_hogar="2 a 3",
            estrato="5",
        )
        datos = extract_exam_export_data(ve, campos_solicitados=["resultados_tabla"])
        filas = json.loads(datos["resultados_tabla"])
        self.assertGreaterEqual(len(filas), 10)
        nombres = [f for f in filas if f["parametro"] == "Nombres y apellidos"]
        self.assertEqual(nombres[0]["resultado"], "Blanca Arango Arango")
        motivo = extract_exam_export_data(ve, campos_solicitados=["motivo_consulta"])
        self.assertEqual(motivo.get("motivo_consulta"), "")
        self.assertIn("resultados_tabla", motivo)
