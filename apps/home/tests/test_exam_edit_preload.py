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

    def test_cognitivo_anamnesis_preload_scalars_and_children(self):
        from apps.home.models import (
            ActividadCompleja,
            ActividadVidaDiaria,
            ActitudCognitiva,
            AtencionCognitiva,
            CognitivoAnamnesisResult,
            ErrorLenguajeCognitivo,
        )

        ve = self._ve(20, "Cognitivo_Anamnesis")
        result = CognitivoAnamnesisResult.objects.create(
            visita_examen=ve,
            motivo_consulta="Olvidos frecuentes",
            descripcion_general="Paciente refiere fallas de memoria",
            apariencia_estado="Adecuada",
            memoria_quejas="Si",
            independencia_vida_diaria="si",
        )
        ActitudCognitiva.objects.create(anamnesis=result, tipo="Colaborador")
        ActitudCognitiva.objects.create(anamnesis=result, tipo="Amable")
        AtencionCognitiva.objects.create(
            anamnesis=result,
            tipo="Quejas atencionales",
            edad_inicio="60",
            caracteristicas="Se distrae fácil",
        )
        ErrorLenguajeCognitivo.objects.create(
            anamnesis=result, tipo="Errores semánticos"
        )
        ActividadVidaDiaria.objects.create(anamnesis=result, tipo="comer")
        ActividadCompleja.objects.create(anamnesis=result, tipo="telefono")

        model = get_exam_model(20)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 20, model)
        self.assertTrue(modo)
        self.assertEqual(datos["motivo_consulta"], "Olvidos frecuentes")
        self.assertEqual(datos["apariencia_estado"], "Adecuada")
        self.assertEqual(datos["memoria_quejas"], "Si")
        self.assertIn("Colaborador", datos["actitudes_tipos"])
        self.assertIn("Amable", datos["actitudes_tipos"])
        self.assertIn("Quejas atencionales", datos["atencion_tipos"])
        self.assertEqual(
            datos["atencion_map"]["Quejas atencionales"]["edad_inicio"], "60"
        )
        self.assertEqual(
            datos["atencion_map"]["Quejas atencionales"]["prefix"], "quejas"
        )
        self.assertIn("Errores semánticos", datos["errores_lenguaje_tipos"])
        self.assertIn("comer", datos["actividades_vida_diaria_tipos"])
        self.assertIn("telefono", datos["actividades_complejas_tipos"])

    def test_medicamentos_extra_datos_medicamentos_json(self):
        from apps.home.models import Medicamento, MedicamentosResult

        ve = self._ve(8, "General_Medicamentos")
        result = MedicamentosResult.objects.create(visita_examen=ve)
        Medicamento.objects.create(
            medicamentos_result=result,
            nombre_comercial="Losartan",
            presentacion="tableta",
            concentracion="50",
            unidad="miligramos",
            via_administracion="oral",
            cantidad="1 tableta",
            frecuencia="Cada 24 horas",
            fecha_inicio="2024-01-01",
            indicacion="HTA",
        )
        model = get_exam_model(8)
        datos, modo, extra = build_datos_examen_edicion(ve, self.paciente, 8, model)
        self.assertTrue(modo)
        self.assertEqual(len(datos["medicamentos"]), 1)
        self.assertIn("datos_medicamentos", extra)
        self.assertIn("Losartan", extra["datos_medicamentos"])

    def test_revision_sistemas_preload_detalles(self):
        from apps.home.models import DetalleRevisionSistemas, RevisionSistemasResult

        ve = self._ve(4, "General_RevisiónSistemas")
        result = RevisionSistemasResult.objects.create(
            visita_examen=ve,
            sintoma_general="si",
            sintoma_cardiopulmonar="no",
        )
        DetalleRevisionSistemas.objects.create(
            revision_sistemas_result=result,
            sistema="general",
            sintoma="Fiebre",
            tiempo="2 días",
            caracteristicas="Intermitente",
        )
        model = get_exam_model(4)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 4, model)
        self.assertTrue(modo)
        self.assertEqual(datos["sintoma_general"], "si")
        self.assertEqual(datos["sistemas_detalles"]["general"][0]["sintoma"], "Fiebre")

    def test_adherencia_preload_scalar(self):
        from apps.home.models import AdherenciaTerapeuticaResult

        ve = self._ve(28, "Adherencia_Terapeutica")
        AdherenciaTerapeuticaResult.objects.create(
            visita_examen=ve,
            dieta_rigurosa="4",
            asistir_consultas="5",
            pendiente_sintomas="3",
            recomendacion_medico="4",
            alimentos_permitidos="3",
            seguir_tratamiento="5",
            regresar_consulta="4",
            seguridad_tratamiento="5",
            olvido_medicamentos="1",
            dejar_tratamiento="0",
            sin_mejoria="1",
            hacer_ejercicio="2",
            recordar_medicamentos="4",
            analisis_periodicos="5",
            confianza_medico="5",
            mejorar_enfermedad="4",
            apego_tratamiento="5",
            adherencia_tratamiento="4",
            menos_medicamento="1",
            confianza_medicamento="5",
            dosis_indicada="5",
            revisiones_periodicas="4",
            medico_sintoma="3",
            mejoria_salud="4",
            sintomas_deterioro="3",
            mediciones_indicadas="4",
            respeto_dieta="3",
            modificacion_tratamiento="1",
            mantener_controlado="5",
            seguridad_resultados="4",
            factor1=50,
            factor2=20,
            factor3=10,
        )
        model = get_exam_model(28)
        datos, modo, _ = build_datos_examen_edicion(ve, self.paciente, 28, model)
        self.assertTrue(modo)
        self.assertEqual(datos["dieta_rigurosa"], "4")
        self.assertEqual(datos["factor1"], 50)
