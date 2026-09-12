# -*- encoding: utf-8 -*-
"""Tests del plan de visitas programadas (épica D) — presets de frecuencia."""
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.home.models import (
    DatosDemograficos,
    Examen,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
)
from apps.home.services.plan_visitas import (
    MAX_FECHAS_SERIE,
    abrir_visita,
    cancelar_resto_serie,
    crear_serie,
    generar_fechas,
)
from apps.home.services.visita_sueno import resolver_visita_sueno


def _paciente(suffix="plan"):
    return DatosDemograficos.objects.create(
        primer_nombre="Luis",
        primer_apellido="Prueba",
        numero_documento=f"PLAN-{suffix}",
        fecha_nacimiento="1985-06-01",
        edad=40,
        celular=f"300{suffix[-4:].zfill(4)}000",
        correo=f"plan.{suffix}@example.com",
    )


class GenerarFechasTests(TestCase):
    def test_diario(self):
        fechas = generar_fechas(date(2026, 1, 1), date(2026, 1, 4), "diario")
        self.assertEqual(
            fechas,
            [
                date(2026, 1, 1),
                date(2026, 1, 2),
                date(2026, 1, 3),
                date(2026, 1, 4),
            ],
        )

    def test_semanal(self):
        # 2026-01-01 es jueves → todos los jueves
        fechas = generar_fechas(date(2026, 1, 1), date(2026, 1, 22), "semanal")
        self.assertEqual(
            fechas,
            [
                date(2026, 1, 1),
                date(2026, 1, 8),
                date(2026, 1, 15),
                date(2026, 1, 22),
            ],
        )

    def test_lv_omite_fin_de_semana(self):
        # 2026-01-01 jueves … 2026-01-06 martes
        fechas = generar_fechas(date(2026, 1, 1), date(2026, 1, 6), "lv")
        self.assertEqual(
            fechas,
            [
                date(2026, 1, 1),  # jue
                date(2026, 1, 2),  # vie
                # sáb 3 y dom 4 omitidos
                date(2026, 1, 5),  # lun
                date(2026, 1, 6),  # mar
            ],
        )

    def test_custom_lun_mie(self):
        # 2026-01-05 lun … 2026-01-14 mié
        fechas = generar_fechas(
            date(2026, 1, 5), date(2026, 1, 14), "custom", dias_semana=[0, 2]
        )
        self.assertEqual(
            fechas,
            [
                date(2026, 1, 5),   # lun
                date(2026, 1, 7),   # mié
                date(2026, 1, 12),  # lun
                date(2026, 1, 14),  # mié
            ],
        )

    def test_custom_sin_dias_falla(self):
        with self.assertRaises(ValidationError):
            generar_fechas(date(2026, 1, 1), date(2026, 1, 10), "custom", dias_semana=[])

    def test_tope_24(self):
        fechas = generar_fechas(date(2026, 1, 1), date(2030, 1, 1), "diario")
        self.assertEqual(len(fechas), MAX_FECHAS_SERIE)

    def test_fin_antes_inicio(self):
        with self.assertRaises(ValidationError):
            generar_fechas(date(2026, 2, 1), date(2026, 1, 1), "diario")


class CrearSerieTests(TestCase):
    def setUp(self):
        self.proyecto = Proyecto.objects.create(nombre="Proyecto Plan")
        self.examen = Examen.objects.create(nombre="Epworth", categoria="SUENO")
        self.tipo = TipoVisita.objects.create(
            nombre="Seguimiento",
            proyecto=self.proyecto,
            examenes=[{"id": self.examen.id, "nombre": "Epworth"}],
        )
        self.paciente = _paciente("crear")
        self.proyecto.pacientes.add(self.paciente)
        self.user = User.objects.create_user("eval", password="x")

    def test_crea_programadas_sin_examenes(self):
        # Semanal desde 1 mar (dom) hasta 29 mar → 5 domingos
        serie, creadas, omitidas = crear_serie(
            paciente=self.paciente,
            tipo_visita=self.tipo,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 29),
            frecuencia_unidad="semanal",
            evaluador=self.user,
            examen_ids=[self.examen.id],
        )
        self.assertEqual(omitidas, 0)
        self.assertEqual(len(creadas), 5)
        self.assertTrue(serie.activa)
        self.assertEqual(serie.frecuencia_unidad, "semanal")
        for v in creadas:
            self.assertEqual(v.estado_visita, "programada")
            self.assertEqual(v.serie_id, serie.id)
            self.assertEqual(v.visita_examenes.count(), 0)

    def test_lv_persiste_dias(self):
        serie, creadas, _ = crear_serie(
            paciente=self.paciente,
            tipo_visita=self.tipo,
            fecha_inicio=date(2026, 1, 5),
            fecha_fin=date(2026, 1, 9),
            frecuencia_unidad="lv",
            examen_ids=[self.examen.id],
        )
        self.assertEqual(serie.dias_semana, [0, 1, 2, 3, 4])
        self.assertEqual(serie.frecuencia_legible(), "L-V")
        self.assertEqual(len(creadas), 5)

    def test_custom_persiste_dias(self):
        serie, creadas, _ = crear_serie(
            paciente=self.paciente,
            tipo_visita=self.tipo,
            fecha_inicio=date(2026, 1, 5),
            fecha_fin=date(2026, 1, 14),
            frecuencia_unidad="custom",
            dias_semana=[0, 2],
            examen_ids=[self.examen.id],
        )
        self.assertEqual(serie.dias_semana, [0, 2])
        self.assertEqual(serie.frecuencia_legible(), "Lun, Mié")
        self.assertEqual(len(creadas), 4)

    def test_omite_fecha_existente(self):
        Visita.objects.create(
            paciente=self.paciente,
            nombre="Ya existe",
            Tipo_visita=self.tipo,
            fecha=date(2026, 3, 1),
            estado_visita="abierta",
        )
        serie, creadas, omitidas = crear_serie(
            paciente=self.paciente,
            tipo_visita=self.tipo,
            fecha_inicio=date(2026, 3, 1),
            fecha_fin=date(2026, 3, 15),
            frecuencia_unidad="semanal",
            examen_ids=[self.examen.id],
        )
        self.assertEqual(omitidas, 1)
        self.assertEqual(len(creadas), 2)
        self.assertEqual(creadas[0].fecha, date(2026, 3, 8))

    def test_paciente_fuera_de_proyecto(self):
        otro = _paciente("fuera")
        with self.assertRaises(ValidationError):
            crear_serie(
                paciente=otro,
                tipo_visita=self.tipo,
                fecha_inicio=date(2026, 1, 1),
                fecha_fin=date(2026, 2, 1),
                frecuencia_unidad="semanal",
            )


class AbrirYCancelarTests(TestCase):
    def setUp(self):
        self.proyecto = Proyecto.objects.create(nombre="Proyecto Abrir")
        self.examen = Examen.objects.create(nombre="ISI", categoria="SUENO")
        self.tipo = TipoVisita.objects.create(
            nombre="Control",
            proyecto=self.proyecto,
            examenes=[{"id": self.examen.id}],
        )
        self.paciente = _paciente("abrir")
        self.proyecto.pacientes.add(self.paciente)
        self.serie, self.creadas, _ = crear_serie(
            paciente=self.paciente,
            tipo_visita=self.tipo,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 15),
            frecuencia_unidad="semanal",
            examen_ids=[self.examen.id],
        )

    def test_abrir_crea_examenes(self):
        visita = self.creadas[0]
        abierta = abrir_visita(visita)
        self.assertEqual(abierta.estado_visita, "abierta")
        self.assertEqual(abierta.visita_examenes.count(), 1)
        ve = abierta.visita_examenes.get()
        self.assertEqual(ve.examen_id, self.examen.id)
        self.assertEqual(ve.estado, "pendiente")

    def test_abrir_no_programada_falla(self):
        visita = self.creadas[0]
        abrir_visita(visita)
        with self.assertRaises(ValidationError):
            abrir_visita(visita)

    def test_cancelar_resto_no_borra_abiertas(self):
        abierta = abrir_visita(self.creadas[0])
        restantes = len(self.creadas) - 1
        deleted = cancelar_resto_serie(self.serie)
        self.assertEqual(deleted, restantes)
        self.serie.refresh_from_db()
        self.assertFalse(self.serie.activa)
        abierta.refresh_from_db()
        self.assertEqual(abierta.estado_visita, "abierta")
        self.assertEqual(
            Visita.objects.filter(serie=self.serie, estado_visita="programada").count(),
            0,
        )


class AnosognosiaProgramadaTests(TestCase):
    def setUp(self):
        self.proyecto = Proyecto.objects.create(nombre="Anosognosia")
        self.tipo = TipoVisita.objects.create(
            nombre="PosIntervención",
            proyecto=self.proyecto,
            examenes=[],
        )
        self.paciente = _paciente("ang")
        self.proyecto.pacientes.add(self.paciente)

    def test_programada_no_asigna_codigo(self):
        Visita.objects.create(
            paciente=self.paciente,
            nombre="PosIntervención",
            Tipo_visita=self.tipo,
            fecha=date(2026, 5, 1),
            estado_visita="programada",
        )
        self.paciente.refresh_from_db()
        self.assertFalse(self.paciente.codigo)

    def test_abrir_asigna_codigo(self):
        visita = Visita.objects.create(
            paciente=self.paciente,
            nombre="PosIntervención",
            Tipo_visita=self.tipo,
            fecha=date(2026, 5, 1),
            estado_visita="programada",
        )
        abrir_visita(visita)
        self.paciente.refresh_from_db()
        self.assertTrue(self.paciente.codigo.startswith("ANG-"))


@override_settings(SUENO_PROYECTO_ID=11, SUENO_TIPO_VISITA_IDS=[20, 7])
class ResolverSuenoIgnoraProgramadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.proyecto = Proyecto.objects.create(
            id=11, nombre="Caracterización del Sueño"
        )
        cls.tipo = TipoVisita.objects.create(
            id=20, nombre="Inicial", proyecto=cls.proyecto
        )
        cls.examen = Examen.objects.create(id=14, nombre="Epworth", categoria="SUENO")
        cls.paciente = _paciente("sueno-prog")

    def test_ignora_programada(self):
        Visita.objects.create(
            paciente=self.paciente,
            nombre="Futura",
            Tipo_visita=self.tipo,
            fecha=date(2026, 12, 1),
            estado_visita="programada",
        )
        abierta = Visita.objects.create(
            paciente=self.paciente,
            nombre="Actual",
            Tipo_visita=self.tipo,
            fecha=date(2026, 1, 1),
            estado_visita="abierta",
        )
        VisitaExamen.objects.create(
            visita=abierta, examen=self.examen, estado="pendiente"
        )
        resuelta = resolver_visita_sueno(self.paciente)
        self.assertEqual(resuelta.id, abierta.id)
