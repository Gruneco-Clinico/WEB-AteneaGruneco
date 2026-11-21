# -*- encoding: utf-8 -*-
"""Pruebas unitarias del cruce Anosognosia × PostHog por horario."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, override_settings

from apps.home.services import recuerdame_anosognosia_cruce as cruce

ZONA = ZoneInfo("America/Bogota")


class VentanaClinicaTests(SimpleTestCase):
    def test_ventana_con_tolerancia(self):
        inicio, fin, meta = cruce.construir_ventana_clinica(
            date(2026, 8, 3), "10:30", "11:30"
        )
        self.assertTrue(meta["tiene_horas"])
        self.assertEqual(inicio, datetime(2026, 8, 3, 10, 15, 0, tzinfo=ZONA))
        self.assertEqual(fin, datetime(2026, 8, 3, 11, 45, 0, tzinfo=ZONA))
        self.assertFalse(meta["solapamiento_amplio"])

    def test_cruza_medianoche(self):
        inicio, fin, meta = cruce.construir_ventana_clinica(
            date(2026, 8, 3), "22:00", "01:00"
        )
        self.assertTrue(meta["tiene_horas"])
        self.assertEqual(inicio.day, 3)
        self.assertEqual(fin.day, 4)
        # 22:00–01:00 + ±15 min → > 2 h efectivas
        self.assertTrue(meta["solapamiento_amplio"])

    def test_sin_hora(self):
        inicio, fin, meta = cruce.construir_ventana_clinica(date(2026, 8, 3), "", "")
        self.assertIsNone(inicio)
        self.assertFalse(meta["tiene_horas"])


class ClasificacionMatchTests(SimpleTestCase):
    def test_horario_unico(self):
        r = cruce.clasificar_match_horario(1, 1)
        self.assertEqual(r["match_scope"], "paciente")
        self.assertEqual(r["match_origen"], "horario_unico")
        self.assertEqual(r["match_confianza"], "alta")
        self.assertEqual(r["atribuible"], "sí")

    def test_m1_n_mayor(self):
        r = cruce.clasificar_match_horario(8, 1)
        self.assertEqual(r["match_scope"], "franja")
        self.assertEqual(r["match_origen"], "horario_grupo")
        self.assertEqual(r["match_confianza"], "baja")
        self.assertEqual(r["atribuible"], "no")

    def test_grupo_media(self):
        r = cruce.clasificar_match_horario(8, 6)
        self.assertEqual(r["match_scope"], "franja")
        self.assertEqual(r["match_confianza"], "media")
        self.assertEqual(r["atribuible"], "no")

    def test_solapamiento_amplio_baja(self):
        r = cruce.clasificar_match_horario(2, 3, solapamiento_amplio=True)
        self.assertEqual(r["match_confianza"], "baja")

    def test_sin_personas(self):
        r = cruce.clasificar_match_horario(3, 0)
        self.assertEqual(r["match_scope"], "ninguno")


class PersonasEnVentanaTests(SimpleTestCase):
    def test_filtra_por_intervalo(self):
        inicio = datetime(2026, 8, 3, 10, 15, tzinfo=ZONA)
        fin = datetime(2026, 8, 3, 11, 45, tzinfo=ZONA)
        actividad = [
            {"person_id": "a", "timestamp": datetime(2026, 8, 3, 10, 40, tzinfo=ZONA)},
            {"person_id": "b", "timestamp": datetime(2026, 8, 3, 9, 0, tzinfo=ZONA)},
            {"person_id": "a", "timestamp": datetime(2026, 8, 3, 11, 0, tzinfo=ZONA)},
        ]
        ids = cruce.personas_en_ventana(actividad, inicio, fin)
        self.assertEqual(ids, {"a"})


class EnriquecerFilasTests(SimpleTestCase):
    def _sesion(self, paciente_id, fecha, hi, hf, correo=""):
        return {
            "paciente_id": paciente_id,
            "documento": str(paciente_id),
            "nombre": f"P{paciente_id}",
            "correo": correo,
            "visita_examen_id": paciente_id,
            "sesion_no": "1",
            "fecha": fecha.isoformat(),
            "fecha_obj": fecha,
            "hora_inicio": hi,
            "hora_final": hf,
            "asistencia": "",
            "asistio": "",
            "nivel_participacion": "",
            "destreza": "",
            "estado_participante": "",
            "tematica": "",
            "observaciones": "",
        }

    def test_email_prioridad_sobre_horario(self):
        fecha = date(2026, 8, 3)
        sesiones = [self._sesion(1, fecha, "10:30", "11:30", correo="a@example.com")]
        usuarios = [
            {
                "person_id": "email-person",
                "email": "a@example.com",
                "adherencia": 0.5,
                "sesiones": 3,
                "pageviews": 10,
                "amplitud_secciones": 2,
                "rol_aproximado": "participante",
                "dispositivo_principal": "mobile",
            }
        ]
        actividad = [
            {
                "person_id": "otra",
                "timestamp": datetime(2026, 8, 3, 10, 40, tzinfo=ZONA),
            }
        ]
        filas, _ = cruce._enriquecer_filas(sesiones, usuarios, {}, actividad, {}, {})
        self.assertEqual(filas[0]["match_origen"], "email")
        self.assertEqual(filas[0]["person_id"], "email-person")
        self.assertEqual(filas[0]["match_confianza"], "alta")

    def test_horario_unico_asigna_biomarcadores(self):
        fecha = date(2026, 8, 3)
        sesiones = [self._sesion(1, fecha, "10:30", "11:30")]
        usuarios = [
            {
                "person_id": "u1",
                "email": "",
                "adherencia": 0.4,
                "sesiones": 5,
                "pageviews": 20,
                "amplitud_secciones": 3,
                "rol_aproximado": "participante",
                "dispositivo_principal": "tablet",
            }
        ]
        actividad = [
            {
                "person_id": "u1",
                "timestamp": datetime(2026, 8, 3, 10, 40, tzinfo=ZONA),
            }
        ]
        filas, _ = cruce._enriquecer_filas(sesiones, usuarios, {}, actividad, {}, {})
        self.assertEqual(filas[0]["match_origen"], "horario_unico")
        self.assertEqual(filas[0]["match_scope"], "paciente")
        self.assertEqual(filas[0]["person_id"], "u1")
        self.assertEqual(filas[0]["sesiones_posthog"], 5)
        self.assertEqual(filas[0]["atribuible"], "sí")

    def test_grupo_sin_biomarcadores_individuales(self):
        fecha = date(2026, 8, 3)
        sesiones = [
            self._sesion(1, fecha, "10:30", "11:30"),
            self._sesion(2, fecha, "10:30", "11:30"),
        ]
        usuarios = [
            {
                "person_id": "u1",
                "adherencia": 0.5,
                "sesiones": 2,
                "pageviews": 4,
            },
            {
                "person_id": "u2",
                "adherencia": 0.3,
                "sesiones": 3,
                "pageviews": 6,
            },
        ]
        actividad = [
            {
                "person_id": "u1",
                "timestamp": datetime(2026, 8, 3, 10, 40, tzinfo=ZONA),
            },
            {
                "person_id": "u2",
                "timestamp": datetime(2026, 8, 3, 11, 0, tzinfo=ZONA),
            },
        ]
        filas, _ = cruce._enriquecer_filas(sesiones, usuarios, {}, actividad, {}, {})
        for fila in filas:
            self.assertEqual(fila["match_scope"], "franja")
            self.assertEqual(fila["match_origen"], "horario_grupo")
            self.assertEqual(fila["atribuible"], "no")
            self.assertEqual(fila["person_id"], "")
            self.assertEqual(fila["adherencia_pct"], "")
            self.assertIn("u1", fila["person_ids_candidatos"])
            self.assertEqual(fila["franja_sesiones_suma"], 5)

    def test_m1_n_mayor_no_atribuye_a_pacientes(self):
        fecha = date(2026, 8, 3)
        sesiones = [
            self._sesion(1, fecha, "10:30", "11:30"),
            self._sesion(2, fecha, "10:30", "11:30"),
        ]
        actividad = [
            {
                "person_id": "solo",
                "timestamp": datetime(2026, 8, 3, 10, 40, tzinfo=ZONA),
            }
        ]
        filas, franjas = cruce._enriquecer_filas(
            sesiones, [], {}, actividad, {}, {}
        )
        for fila in filas:
            self.assertEqual(fila["match_confianza"], "baja")
            self.assertEqual(fila["atribuible"], "no")
            self.assertEqual(fila["person_id"], "")
            self.assertEqual(fila["person_ids_candidatos"], "solo")
        slot = franjas[("2026-08-03", "10:30", "11:30")]
        self.assertEqual(slot["person_ids"], ["solo"])


@override_settings(
    RECUERDAME_STAFF_EMAIL_DOMAINS="gna.org.co",
    RECUERDAME_PERSON_ID_DENYLIST="denied-1",
)
class FiltrosAntiRuidoTests(SimpleTestCase):
    def test_email_staff(self):
        from apps.home.services import recuerdame_analytics as analytics

        self.assertTrue(analytics.es_email_staff("x@gna.org.co"))
        self.assertFalse(analytics.es_email_staff("x@example.com"))

    def test_denylist(self):
        from apps.home.services import recuerdame_analytics as analytics

        self.assertTrue(analytics.es_person_id_denegado("denied-1"))
        self.assertFalse(analytics.es_person_id_denegado("other"))
