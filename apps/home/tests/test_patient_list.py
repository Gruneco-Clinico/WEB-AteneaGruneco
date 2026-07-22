# -*- encoding: utf-8 -*-
"""Tests C-14: paginación y búsqueda del listado de pacientes."""
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.home.models import DatosDemograficos, Proyecto, ProyectoPacienteExtra
from apps.home.views.patients import PACIENTES_POR_PAGINA, _build_codigos_map


class DisableMigrations(dict):
    """Evita migraciones rotas (consentimiento_pdf) al crear la DB de test."""

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


def _make_paciente(i, **kwargs):
    defaults = dict(
        primer_nombre=f"Nombre{i}",
        primer_apellido=f"Apellido{i}",
        numero_documento=f"{1000000 + i}",
        fecha_nacimiento="1990-01-01",
        edad=30 + (i % 40),
        celular=f"300{i:07d}",
        correo=f"pac{i}@example.com",
    )
    defaults.update(kwargs)
    return DatosDemograficos.objects.create(**defaults)


@override_settings(MIGRATION_MODULES=DisableMigrations())
class PatientListPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("listuser", password="pass")
        cls.proyecto_a = Proyecto.objects.create(nombre="Proyecto Alpha")
        cls.proyecto_b = Proyecto.objects.create(nombre="Proyecto Beta")
        cls.pacientes = [_make_paciente(i) for i in range(1, 32)]  # 31
        for pac in cls.pacientes[:5]:
            cls.proyecto_a.pacientes.add(pac)
            ProyectoPacienteExtra.objects.create(
                proyecto=cls.proyecto_a,
                paciente=pac,
                codigo_proyecto=f"A{pac.numero_documento[-4:]}",
            )
        cls.pacientes[10].primer_nombre = "Buscable"
        cls.pacientes[10].primer_apellido = "Unico"
        cls.pacientes[10].save()
        cls.url = reverse("tables.html")

    def setUp(self):
        self.client = Client()
        self.client.login(username="listuser", password="pass")

    def test_requiere_auth(self):
        anon = Client()
        resp = anon.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_pagina_25_registros(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        page = resp.context["page_obj"]
        self.assertEqual(page.paginator.per_page, PACIENTES_POR_PAGINA)
        self.assertEqual(len(page.object_list), PACIENTES_POR_PAGINA)
        self.assertTrue(page.has_next())
        self.assertContains(resp, "Siguiente")
        self.assertContains(resp, "Anterior")

    def test_segunda_pagina(self):
        resp = self.client.get(self.url, {"page": 2})
        self.assertEqual(resp.status_code, 200)
        page = resp.context["page_obj"]
        self.assertEqual(page.number, 2)
        self.assertEqual(len(page.object_list), 6)  # 31 - 25

    def test_filtro_q_por_nombre(self):
        resp = self.client.get(self.url, {"q": "Buscable"})
        self.assertEqual(resp.status_code, 200)
        page = resp.context["page_obj"]
        self.assertEqual(page.paginator.count, 1)
        self.assertEqual(page.object_list[0].primer_nombre, "Buscable")
        self.assertEqual(resp.context["q"], "Buscable")

    def test_filtro_proyecto(self):
        resp = self.client.get(self.url, {"proyecto": str(self.proyecto_a.id)})
        self.assertEqual(resp.status_code, 200)
        page = resp.context["page_obj"]
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(resp.context["filtro_proyecto"], str(self.proyecto_a.id))

    def test_paginacion_conserva_query_params(self):
        resp = self.client.get(
            self.url, {"q": "Apellido", "proyecto": str(self.proyecto_a.id), "page": 1}
        )
        self.assertEqual(resp.status_code, 200)
        pq = resp.context["pagination_query"]
        self.assertIn("q=Apellido", pq)
        self.assertIn(f"proyecto={self.proyecto_a.id}", pq)
        self.assertNotIn("page=", pq)
        # Enlaces de paginación incluyen filtros
        if resp.context["page_obj"].paginator.num_pages > 1:
            self.assertContains(resp, f"proyecto={self.proyecto_a.id}")

    def test_codigos_solo_pagina_visible(self):
        resp = self.client.get(self.url, {"page": 1})
        page = resp.context["page_obj"]
        codigos_map = resp.context["codigos_map"]
        page_ids = {p.id for p in page.object_list}
        self.assertTrue(set(codigos_map.keys()).issubset(page_ids))
        # Reconstruir mapa solo para la página debe coincidir
        rebuilt = _build_codigos_map(page)
        self.assertEqual(set(rebuilt.keys()), set(codigos_map.keys()))
