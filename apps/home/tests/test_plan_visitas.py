# -*- encoding: utf-8 -*-
"""Tests del plan de visitas programadas (épica D) — presets de frecuencia."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

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


class FechasEspecificasTests(TestCase):
    def setUp(self):
        self.proyecto = Proyecto.objects.create(nombre="Proyecto Fechas")
        self.examen = Examen.objects.create(nombre="PSQI", categoria="SUENO")
        self.tipo = TipoVisita.objects.create(
            nombre="Seguimiento fechas",
            proyecto=self.proyecto,
            examenes=[{"id": self.examen.id}],
        )
        self.paciente = _paciente("fechas")
        self.proyecto.pacientes.add(self.paciente)

    def _crear(self, fechas):
        return crear_serie(
            paciente=self.paciente,
            tipo_visita=self.tipo,
            frecuencia_unidad="fechas",
            fechas=fechas,
            examen_ids=[self.examen.id],
        )

    def test_ordena_y_deduplica(self):
        serie, creadas, omitidas = self._crear(
            [date(2026, 4, 20), date(2026, 4, 3), date(2026, 4, 20), date(2026, 4, 10)]
        )
        self.assertEqual(omitidas, 0)
        self.assertEqual(
            [v.fecha for v in creadas],
            [date(2026, 4, 3), date(2026, 4, 10), date(2026, 4, 20)],
        )
        self.assertEqual(serie.fecha_inicio, date(2026, 4, 3))
        self.assertEqual(serie.fecha_fin, date(2026, 4, 20))
        self.assertEqual(serie.frecuencia_unidad, "fechas")
        self.assertEqual(serie.dias_semana, [])
        for v in creadas:
            self.assertEqual(v.estado_visita, "programada")
            self.assertEqual(v.serie_id, serie.id)

    def test_lista_vacia_falla(self):
        with self.assertRaises(ValidationError):
            self._crear([])

    def test_mas_de_24_falla(self):
        fechas = [date(2026, 1, 1) + timedelta(days=i) for i in range(MAX_FECHAS_SERIE + 1)]
        with self.assertRaises(ValidationError):
            self._crear(fechas)

    def test_omite_fecha_existente(self):
        Visita.objects.create(
            paciente=self.paciente,
            nombre="Ya existe",
            Tipo_visita=self.tipo,
            fecha=date(2026, 5, 7),
            estado_visita="abierta",
        )
        _serie, creadas, omitidas = self._crear([date(2026, 5, 7), date(2026, 5, 14)])
        self.assertEqual(omitidas, 1)
        self.assertEqual([v.fecha for v in creadas], [date(2026, 5, 14)])

    def test_frecuencia_legible(self):
        serie, _, _ = self._crear([date(2026, 6, 1)])
        self.assertEqual(serie.frecuencia_legible(), "Fechas específicas")

    def test_acepta_fecha_pasada(self):
        pasada = date.today() - timedelta(days=30)
        _serie, creadas, _ = self._crear([pasada])
        self.assertEqual([v.fecha for v in creadas], [pasada])


class CrearPlanVisitasVistaTests(TestCase):
    def setUp(self):
        self.proyecto = Proyecto.objects.create(nombre="Proyecto Vista")
        self.examen = Examen.objects.create(nombre="ESS", categoria="SUENO")
        self.tipo = TipoVisita.objects.create(
            nombre="Control vista",
            proyecto=self.proyecto,
            examenes=[{"id": self.examen.id}],
        )
        self.paciente = _paciente("vista")
        self.proyecto.pacientes.add(self.paciente)
        self.user = User.objects.create_user("eval-vista", password="x")
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("crear_plan_visitas", args=[self.paciente.id])

    def test_post_fechas_especificas_sin_rango(self):
        resp = self.client.post(
            self.url,
            {
                "tipo_visita": self.tipo.id,
                "frecuencia_unidad": "fechas",
                "fechas": ["2026-07-15", "2026-07-02", "2026-07-09"],
                "examenes_seleccionados": [self.examen.id],
            },
        )
        self.assertEqual(resp.status_code, 302)
        visitas = Visita.objects.filter(paciente=self.paciente).order_by("fecha")
        self.assertEqual(
            [v.fecha for v in visitas],
            [date(2026, 7, 2), date(2026, 7, 9), date(2026, 7, 15)],
        )
        self.assertTrue(all(v.estado_visita == "programada" for v in visitas))
        serie = visitas[0].serie
        self.assertEqual(serie.frecuencia_unidad, "fechas")
        self.assertEqual(serie.fecha_inicio, date(2026, 7, 2))
        self.assertEqual(serie.fecha_fin, date(2026, 7, 15))

    def test_post_fecha_invalida_no_crea(self):
        resp = self.client.post(
            self.url,
            {
                "tipo_visita": self.tipo.id,
                "frecuencia_unidad": "fechas",
                "fechas": ["2026-07-02", "no-es-fecha"],
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Visita.objects.filter(paciente=self.paciente).exists())


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
