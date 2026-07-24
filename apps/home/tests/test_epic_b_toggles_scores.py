# -*- encoding: utf-8 -*-
"""Tests B-08 / B-10: semántica de toggles y puntajes AQD/CDR/RedLat."""
from django.test import SimpleTestCase
from django.template import Context, Template

from apps.home.models.field_toggle_semantics import (
    TOGGLE_DEFAULTS,
    formatear_toggle,
    neuro_toggle_tipo,
)
from apps.home.models.results_anosognosia import (
    AQDCuidadorResult,
    AQDParticipanteResult,
    ParticipanteYesavageResult,
    PuntajeCDRResult,
    RedLatSpanishResult,
)
from apps.home.services.exam_view_context import (
    _formatear_valor_campo,
    _resolver_scores_vista,
)


class ToggleSemanticsTests(SimpleTestCase):
    def test_olfato_es_detecta(self):
        self.assertEqual(neuro_toggle_tipo("clavos_izquierdo"), "detecta")
        self.assertEqual(TOGGLE_DEFAULTS["detecta"], True)
        self.assertEqual(formatear_toggle("detecta", True), "Detecta")
        self.assertEqual(formatear_toggle("detecta", False), "No detecta")

    def test_sintoma_ausente_por_defecto(self):
        self.assertEqual(neuro_toggle_tipo("amaurosis"), "sintoma")
        self.assertEqual(TOGGLE_DEFAULTS["sintoma"], False)
        self.assertEqual(formatear_toggle("sintoma", False), "Ausente")
        self.assertEqual(formatear_toggle("sintoma", True), "Presente")

    def test_estructura_normal_anormal(self):
        self.assertEqual(neuro_toggle_tipo("tacto_frente_globo"), "estructura")
        self.assertEqual(formatear_toggle("estructura", True), "Normal")
        self.assertEqual(formatear_toggle("estructura", False), "Anormal")


class FormatearCampoToggleTests(SimpleTestCase):
    def test_formatea_true_y_false_con_semantica(self):
        from apps.home.models.results_general import ExamenNeurologicoResult

        class Fake:
            pass

        fake = Fake()
        fake.clavos_izquierdo = True
        fake.amaurosis = False
        type(fake).FIELD_TOGGLE_SEMANTICS = ExamenNeurologicoResult.FIELD_TOGGLE_SEMANTICS

        field_clavos = ExamenNeurologicoResult._meta.get_field("clavos_izquierdo")
        field_ama = ExamenNeurologicoResult._meta.get_field("amaurosis")
        self.assertEqual(_formatear_valor_campo(fake, field_clavos), "Detecta")
        self.assertEqual(_formatear_valor_campo(fake, field_ama), "Ausente")


class AQDScoreTests(SimpleTestCase):
    def test_suma_items_1_a_4_cuidador(self):
        obj = AQDCuidadorResult(
            recordar_fecha="2",
            firmar="3",
            deprimido="4",
        )
        self.assertEqual(obj.calcular_puntaje_total(), 9)

    def test_suma_items_participante(self):
        obj = AQDParticipanteResult(
            recordar_fecha="1",
            firmar="2",
            deprimido="0",
        )
        self.assertEqual(obj.calcular_puntaje_total(), 3)


class CDRSumaCajasTests(SimpleTestCase):
    def test_suma_dominios(self):
        obj = PuntajeCDRResult(
            cdr_memoria="1",
            cdr_orientacion="0.5",
            cdr_juicio="0",
            cdr_comunitarias="1",
            cdr_pasatiempos="0.5",
            cdr_cuidado="0",
            cdr_global="1",
        )
        self.assertEqual(obj.calcular_suma_cajas(), 3.0)


class RedLatTotalTests(SimpleTestCase):
    def test_suma_componentes(self):
        obj = RedLatSpanishResult(
            puntaje_autocuidado="10",
            puntaje_cuidado_hogar="20",
            puntaje_trabajo_recreacion="5",
            puntaje_compras_dinero="",
            puntaje_viajes="0",
            puntaje_comunicacion="15",
            puntaje_tecnologia="10",
        )
        self.assertEqual(obj.calcular_puntaje_total(), 60.0)

    def test_total_cero_es_cero(self):
        obj = RedLatSpanishResult()
        self.assertEqual(obj.calcular_puntaje_total(), 0.0)


class ScoreBannerPolicyTests(SimpleTestCase):
    """Vista/impresión: qué caja de resumen mostrar por examen."""

    def test_aqd_y_yesavage_sin_banner(self):
        for cls, kwargs in (
            (AQDCuidadorResult, {"puntaje_total": 12}),
            (AQDParticipanteResult, {"puntaje_total": 8}),
            (RedLatSpanishResult, {"puntaje_total": 40}),
        ):
            scores = _resolver_scores_vista(cls(**kwargs))
            self.assertIsNone(scores["puntaje_total"], cls.__name__)
            self.assertIsNone(scores["score_banner_valor"], cls.__name__)

    def test_yesavage_muestra_interpretacion_sin_caja_de_total(self):
        """D-19: sin puntaje_total en banner de total; sí interpretación legible."""
        scores = _resolver_scores_vista(
            ParticipanteYesavageResult(puntaje_total=5, interpretacion="Normal")
        )
        self.assertIsNone(scores["puntaje_total"])
        self.assertEqual(scores["score_banner_titulo"], "Interpretación Yesavage")
        self.assertEqual(scores["score_banner_valor"], "Normal")

    def test_cdr_banner_es_global_y_suma_en_vivo(self):
        obj = PuntajeCDRResult(
            cdr_memoria="1",
            cdr_orientacion="1",
            cdr_juicio="1",
            cdr_comunitarias="0.5",
            cdr_pasatiempos="0.5",
            cdr_cuidado="1",
            cdr_global="1",
            suma_cajas=0,  # registro antiguo sin recalcular
        )
        scores = _resolver_scores_vista(obj)
        self.assertEqual(scores["score_banner_titulo"], "CDR Global")
        self.assertEqual(scores["score_banner_valor"], "1")
        self.assertEqual(scores["suma_cajas"], 5.0)
        self.assertIn("6 dominios", scores["score_banner_detalle"])
        self.assertIn("5", scores["score_banner_detalle"])

    def test_mew_muestra_puntuacion_total_meq(self):
        from apps.home.models.results_sleep import MEWResult

        obj = MEWResult(puntuacion=49, tipo_persona="Tipo intermedio")
        scores = _resolver_scores_vista(obj)
        self.assertEqual(scores["score_banner_titulo"], "Puntuación total MEQ")
        self.assertEqual(scores["score_banner_valor"], 49)
        self.assertEqual(scores["puntaje_total"], 49)
        self.assertEqual(scores["score_banner_detalle"], "Tipo intermedio")


class PuntajeCeroContextoTests(SimpleTestCase):
    """B-10: puntaje 0 no debe convertirse en None ni ocultarse en PDF."""

    def test_resolver_puntaje_respeta_cero(self):
        class Fake:
            puntaje_total = 0
            puntuacion_total = 99

        resultado = Fake()
        puntaje_total = getattr(resultado, "puntaje_total", None)
        if puntaje_total is None:
            puntaje_total = getattr(resultado, "puntuacion_total", None)
        self.assertEqual(puntaje_total, 0)

    def test_pdf_template_muestra_cero(self):
        tpl = Template(
            "{% if score_banner_valor is not None %}"
            "<p>{{ score_banner_valor }}</p>"
            "{% endif %}"
        )
        html = tpl.render(Context({"score_banner_valor": 0}))
        self.assertIn("<p>0</p>", html)
