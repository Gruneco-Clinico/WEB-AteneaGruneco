# -*- encoding: utf-8 -*-
"""Tests seguimiento Caracterización del Sueño — visita activa y portal público."""
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from apps.home.models import (
    DatosDemograficos,
    Proyecto,
    TipoVisita,
    Visita,
    VisitaExamen,
    Examen,
)
from apps.home.services.visita_sueno import (
    resolver_visita_sueno,
    resolver_visita_examen_publico,
    url_examen_publico,
)
from apps.home.tokens import generar_token_paciente


def _paciente(suffix="sueno"):
    return DatosDemograficos.objects.create(
        primer_nombre="Ana",
        primer_apellido="Prueba",
        numero_documento=f"SUENO-{suffix}",
        fecha_nacimiento="1990-01-15",
        edad=35,
        celular=f"310000{suffix[-4:].zfill(4)}",
    )


@override_settings(SUENO_PROYECTO_ID=11, SUENO_TIPO_VISITA_IDS=[20, 7])
class ResolverVisitaSuenoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.proyecto = Proyecto.objects.create(
            id=11, nombre="Caracterización del Sueño"
        )
        cls.tipo_inicial = TipoVisita.objects.create(
            id=20, nombre="Inicial", proyecto=cls.proyecto
        )
        cls.tipo_seguimiento = TipoVisita.objects.create(
            id=99, nombre="Seguimiento", proyecto=cls.proyecto
        )
        cls.examen_epworth = Examen.objects.create(
            id=14, nombre="Epworth", categoria="SUENO"
        )
        cls.paciente = _paciente("resolver")

    def test_prioriza_visita_con_examenes_abiertos(self):
        visita_inicial = Visita.objects.create(
            nombre="Inicial",
            paciente=self.paciente,
            Tipo_visita=self.tipo_inicial,
        )
        VisitaExamen.objects.create(
            visita=visita_inicial,
            examen=self.examen_epworth,
            estado="completado",
        )

        visita_seg = Visita.objects.create(
            nombre="Seguimiento",
            paciente=self.paciente,
            Tipo_visita=self.tipo_seguimiento,
        )
        VisitaExamen.objects.create(
            visita=visita_seg,
            examen=self.examen_epworth,
            estado="pendiente",
        )

        visita = resolver_visita_sueno(self.paciente)
        self.assertEqual(visita.id, visita_seg.id)

    def test_visita_id_explicito(self):
        visita = Visita.objects.create(
            nombre="Inicial",
            paciente=self.paciente,
            Tipo_visita=self.tipo_inicial,
        )
        resuelta = resolver_visita_sueno(self.paciente, visita_id=visita.id)
        self.assertEqual(resuelta.id, visita.id)

    def test_url_examen_publico_incluye_visita_id(self):
        visita = Visita.objects.create(
            nombre="Inicial",
            paciente=self.paciente,
            Tipo_visita=self.tipo_inicial,
        )
        url = url_examen_publico(
            "/guardar-examen-publico-epworth/", self.paciente.id, visita.id
        )
        self.assertIn("visita_id=", url)
        self.assertIn("token=", url)


@override_settings(SUENO_PROYECTO_ID=11, SUENO_TIPO_VISITA_IDS=[20, 7])
class ConsultaExamenesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.proyecto = Proyecto.objects.get_or_create(
            id=11, defaults={"nombre": "Caracterización del Sueño"}
        )[0]
        self.tipo_seg = TipoVisita.objects.create(
            nombre="Seguimiento CSV", proyecto=self.proyecto
        )
        self.paciente = _paciente("consulta")
        self.examen = Examen.objects.create(
            id=16, nombre="MEW", categoria="SUENO"
        )
        self.visita = Visita.objects.create(
            nombre="Seg",
            paciente=self.paciente,
            Tipo_visita=self.tipo_seg,
        )
        VisitaExamen.objects.create(
            visita=self.visita,
            examen=self.examen,
            estado="pendiente",
        )

    def test_consulta_examenes_devuelve_visita_id_en_url(self):
        url = reverse("consulta_examenes")
        response = self.client.get(
            url, {"documento": self.paciente.numero_documento}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["visita_id"], self.visita.id)
        self.assertTrue(any("visita_id=" in e["url"] for e in data["examenes"]))


@override_settings(SUENO_PROYECTO_ID=11, SUENO_TIPO_VISITA_IDS=[20, 7])
class ExamenPublicoGETTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.proyecto = Proyecto.objects.get_or_create(
            id=11, defaults={"nombre": "Caracterización del Sueño"}
        )[0]
        self.tipo = TipoVisita.objects.create(
            id=20, nombre="Inicial pub", proyecto=self.proyecto
        )
        self.paciente = _paciente("publico")
        self.examen = Examen.objects.create(
            id=14, nombre="Epworth pub", categoria="SUENO"
        )
        self.visita_inicial = Visita.objects.create(
            nombre="Inicial",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
        )
        VisitaExamen.objects.create(
            visita=self.visita_inicial,
            examen=self.examen,
            estado="completado",
        )
        self.visita_seg = Visita.objects.create(
            nombre="Seguimiento",
            paciente=self.paciente,
            Tipo_visita=self.tipo,
        )
        VisitaExamen.objects.create(
            visita=self.visita_seg,
            examen=self.examen,
            estado="pendiente",
        )
        self.token = generar_token_paciente(self.paciente.id)

    def test_get_epworth_usa_visita_seguimiento(self):
        _, ve = resolver_visita_examen_publico(
            self.paciente, 14, visita_id=self.visita_seg.id
        )
        self.assertEqual(ve.visita_id, self.visita_seg.id)
        self.assertEqual(ve.estado, "pendiente")

        response = self.client.get(
            "/guardar-examen-publico-epworth/",
            {"token": self.token, "visita_id": self.visita_seg.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "visita_id")
