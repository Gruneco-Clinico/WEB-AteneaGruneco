# -*- encoding: utf-8 -*-
"""Tests Épica D: exam_scoring + banners de interpretación en vista/PDF."""
from django.test import SimpleTestCase

from apps.home.services.exam_scoring import (
    interpretar_epworth,
    interpretar_psqi,
    interpretar_atenas,
    interpretar_isi,
    cronotipo_mew,
    interpretar_stopbang,
    score_berlin,
    interpretar_aqd_anosognosia,
    score_yesavage,
    interpretar_yesavage,
    score_concentracion_moca,
    score_mis_moca,
    score_betty,
    interpretar_betty,
    codigo_estado_eq5d,
    nivel_eq5d,
)
from apps.home.services.exam_view_context import _resolver_scores_vista
from apps.home.models.results_sleep import (
    PittsburghResult,
    EpworthResult,
    AtenasResult,
    ISIResult,
    StopBangResult,
    BerlinResult,
    MEWResult,
)
from apps.home.models.results_anosognosia import (
    BettyFerrelResult,
    MoCAResult,
    ParticipanteYesavageResult,
    EuroQol5D5LResult,
    CuidadorNPIResult,
    AQDCuidadorResult,
    AQDParticipanteResult,
)


class EpworthScoringTests(SimpleTestCase):
    def test_umbrales_acordados(self):
        self.assertEqual(interpretar_epworth(0), "Somnolencia diurna normal")
        self.assertEqual(interpretar_epworth(5), "Somnolencia diurna normal")
        self.assertEqual(interpretar_epworth(6), "Somnolencia diurna media")
        self.assertEqual(interpretar_epworth(10), "Somnolencia diurna media")
        self.assertEqual(interpretar_epworth(11), "Somnolencia diurna moderada")
        self.assertEqual(interpretar_epworth(15), "Somnolencia diurna moderada")
        self.assertEqual(interpretar_epworth(16), "Somnolencia diurna severa")
        self.assertEqual(interpretar_epworth(24), "Somnolencia diurna severa")


class PSQIScoringTests(SimpleTestCase):
    def test_interpretacion(self):
        self.assertIn("bien", interpretar_psqi(5).lower())
        self.assertIn("mal", interpretar_psqi(6).lower())


class AtenasISITests(SimpleTestCase):
    def test_atenas(self):
        self.assertIn("Sin problemas", interpretar_atenas(3))
        self.assertIn("severos", interpretar_atenas(20))

    def test_isi(self):
        self.assertIn("Sin insomnio", interpretar_isi(7))
        self.assertIn("severo", interpretar_isi(22))


class MEWCronotipoTests(SimpleTestCase):
    def test_bandas(self):
        self.assertEqual(cronotipo_mew(70), "Definitivamente matutino")
        self.assertEqual(cronotipo_mew(50), "Ni matutino ni vespertino")
        self.assertEqual(cronotipo_mew(20), "Definitivamente vespertino")


class StopBangScoringTests(SimpleTestCase):
    def test_riesgo(self):
        bajo = interpretar_stopbang(2, 1, 1, False)
        self.assertEqual(bajo["riesgo"], "Bajo")
        alto = interpretar_stopbang(5, 3, 2, False)
        self.assertEqual(alto["riesgo"], "Alto")
        alt = interpretar_stopbang(3, 2, 2, True)
        self.assertEqual(alt["riesgo"], "Alto")


class BerlinScoringTests(SimpleTestCase):
    def test_alto_riesgo_dos_categorias(self):
        data = {
            "tipo_ronquido": "Más fuerte que hablar",
            "frecuencia_ronquidos": "Casi todos los días",
            "ronquido_molesto": "Sí",
            "apnea_observada": "Nunca",
            "fatiga_matutina": "Casi todos los días",
            "fatiga_dia": "3-4 veces por semana",
            "somnolencia_conducir": False,
            "presion_alta": False,
            "imc": 25,
        }
        scored = score_berlin(data)
        self.assertTrue(scored["categoria1_positiva"])
        self.assertTrue(scored["categoria2_positiva"])
        self.assertFalse(scored["categoria3_positiva"])
        self.assertEqual(scored["categorias_positivas"], 2)
        self.assertEqual(scored["riesgo"], "Alto")

    def test_categoria3_hta_o_imc(self):
        scored = score_berlin({"presion_alta": True, "imc": 22})
        self.assertTrue(scored["categoria3_positiva"])
        scored2 = score_berlin({"presion_alta": False, "imc": 31})
        self.assertTrue(scored2["categoria3_positiva"])


class AQDAnosognosiaTests(SimpleTestCase):
    def test_delta_umbral(self):
        con = interpretar_aqd_anosognosia(20, 8)
        self.assertEqual(con["delta"], 12)
        self.assertIn("Con Anosognosia", con["interpretacion"])
        sin = interpretar_aqd_anosognosia(15, 8)
        self.assertEqual(sin["delta"], 7)
        self.assertIn("Sin Anosognosia", sin["interpretacion"])


class YesavageScoringTests(SimpleTestCase):
    def test_recalcula_e_interpreta(self):
        data = {
            "satisfaccion_vida": "no",  # punta
            "disminuir_actividades": "si",  # punta
            "vida_vacia": "no",
            "aburrido_frecuente": "no",
            "buen_animo": "si",
            "preocupacion": "no",
            "felicidad": "si",
            "frecuencia_desamparado": "no",
            "quedarse_casa": "no",
            "problemas_memoria": "no",
            "maravilla_vivir": "si",
            "inutil": "no",
            "lleno_energia": "si",
            "sin_esperanza": "no",
            "otras_personas_mejor": "no",
        }
        scored = score_yesavage(data)
        self.assertEqual(scored["puntaje_total"], 2)
        self.assertEqual(scored["interpretacion"], "Normal")
        self.assertEqual(interpretar_yesavage(8), "Depresión leve")
        self.assertEqual(interpretar_yesavage(12), "Depresión establecida")


class MoCAScoringTests(SimpleTestCase):
    def test_item6_concentracion(self):
        pts, res = score_concentracion_moca(0)
        self.assertEqual((pts, res), (1, "no_fallo"))
        pts, res = score_concentracion_moca(1)
        self.assertEqual((pts, res), (1, "no_fallo"))
        pts, res = score_concentracion_moca(2)
        self.assertEqual((pts, res), (0, "fallo"))

    def test_mis(self):
        # 2 free, 1 category, 1 multiple, 1 none → 3+3+2+1 = 9
        mis = score_mis_moca(
            [True, True, False, False, False],
            [False, False, True, False, False],
            [False, False, False, True, False],
        )
        self.assertEqual(mis, 9)


class BettyScoringTests(SimpleTestCase):
    def test_inversion_y_terciles(self):
        # Ítem positivo esperanza=4 → invertido a 1 (bajo problema)
        data = {
            "agotamiento": "1",
            "cambios_alimenticios": "1",
            "dolor": "1",
            "cambios_sueno": "1",
            "salud_fisica_general": "4",  # positivo → 1
            "felicidad": "4",
            "esperanza": "4",
            "angustia_tratamiento": "1",
        }
        scored = score_betty(data)
        self.assertIsNotNone(scored["promedio_fisico"])
        self.assertLessEqual(scored["promedio_fisico"], 2.0)
        self.assertIn("alta", interpretar_betty(1.5).lower())
        self.assertIn("media", interpretar_betty(2.5).lower())
        self.assertIn("baja", interpretar_betty(3.5).lower())


class EuroQoLScoringTests(SimpleTestCase):
    def test_codigo_estado(self):
        self.assertEqual(nivel_eq5d("No tengo problemas para caminar"), 1)
        self.assertEqual(nivel_eq5d("Tengo problemas leves para caminar"), 2)
        self.assertEqual(
            codigo_estado_eq5d(
                "No tengo problemas para caminar",
                "No tengo problemas con el cuidado personal",
                "Tengo problemas leves para realizar mis actividades cotidianas",
                "Tengo severo dolor o malestar",
                "Estoy moderadamente ansioso o deprimido",
            ),
            "11243",
        )


class ScoreBannerEpicDTests(SimpleTestCase):
    def test_epworth_muestra_interpretacion(self):
        scores = _resolver_scores_vista(
            EpworthResult(puntaje_total=12, interpretacion="Somnolencia diurna moderada")
        )
        self.assertEqual(scores["score_banner_valor"], 12)
        self.assertIn("moderada", scores["score_banner_detalle"])

    def test_psqi_banner(self):
        scores = _resolver_scores_vista(
            PittsburghResult(
                puntuacion_total=8,
                interpretacion="Duerme mal (mala calidad de sueño)",
                componente_calidad=2,
            )
        )
        self.assertEqual(scores["score_banner_valor"], 8)
        self.assertIn("Duerme mal", scores["score_banner_detalle"])

    def test_berlin_banner(self):
        scores = _resolver_scores_vista(
            BerlinResult(riesgo="Alto", categorias_positivas=2, interpretacion="Alto riesgo")
        )
        self.assertEqual(scores["score_banner_valor"], "Alto")

    def test_stopbang_banner(self):
        scores = _resolver_scores_vista(
            StopBangResult(puntaje_total=6, riesgo="Alto", stop_positivos=3, bang_positivos=3)
        )
        self.assertEqual(scores["score_banner_valor"], 6)
        self.assertIn("STOP", scores["score_banner_detalle"])

    def test_yesavage_muestra_interpretacion_no_cero(self):
        scores = _resolver_scores_vista(
            ParticipanteYesavageResult(puntaje_total=3, interpretacion="0")
        )
        self.assertEqual(scores["score_banner_titulo"], "Interpretación Yesavage")
        self.assertEqual(scores["score_banner_valor"], "Normal")

    def test_aqd_sigue_sin_caja_total(self):
        for cls in (AQDCuidadorResult, AQDParticipanteResult):
            scores = _resolver_scores_vista(cls(puntaje_total=20))
            self.assertIsNone(scores["score_banner_valor"], cls.__name__)

    def test_betty_banner(self):
        scores = _resolver_scores_vista(
            BettyFerrelResult(promedio_global=2.5, interpretacion="Calidad de vida media")
        )
        self.assertEqual(scores["score_banner_valor"], 2.5)

    def test_euroqol_codigo(self):
        scores = _resolver_scores_vista(EuroQol5D5LResult(estado_salud="11243"))
        self.assertEqual(scores["score_banner_valor"], "11243")

    def test_moca_banner_con_mis(self):
        scores = _resolver_scores_vista(
            MoCAResult(puntaje_total=27, interpretacion="Normal", mis=12)
        )
        self.assertEqual(scores["score_banner_valor"], 27)
        self.assertIn("MIS", scores["score_banner_detalle"])

    def test_npi_total_banner(self):
        scores = _resolver_scores_vista(
            CuidadorNPIResult(puntaje_total=40, carga_total=12)
        )
        self.assertEqual(scores["score_banner_titulo"], "Puntaje total NPI")
        self.assertEqual(scores["score_banner_valor"], 40)

    def test_atenas_isi_mew(self):
        self.assertEqual(
            _resolver_scores_vista(AtenasResult(puntuacion_total=4)).get("score_banner_valor"),
            4,
        )
        self.assertEqual(
            _resolver_scores_vista(ISIResult(puntuacion_total=10)).get("score_banner_valor"),
            10,
        )
        self.assertEqual(
            _resolver_scores_vista(
                MEWResult(puntuacion=60, tipo_persona="Moderadamente matutino")
            ).get("score_banner_titulo"),
            "Puntuación total MEQ",
        )
