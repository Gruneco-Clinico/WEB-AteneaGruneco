# -*- encoding: utf-8 -*-
"""Tests calendario disponibilidad — conflictos y bloqueos."""
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from apps.home.models import Sala, DisponibilidadUsuario, BloqueoDisponibilidad
from apps.home.views.scheduling import (
    validar_conflictos_disponibilidad,
    _slot_bloqueado,
    _crear_o_reactivar_disponibilidad,
)


class DisponibilidadConflictosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("prof1", password="x")
        self.otro = User.objects.create_user("prof2", password="x")
        self.sala = Sala.objects.create(nombre="Sala Test")

    def test_validar_conflicto_misma_sala(self):
        lunes = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
        DisponibilidadUsuario.objects.create(
            usuario=self.otro,
            sala=self.sala,
            dia_semana=lunes.weekday(),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            fecha_inicio=lunes,
        )
        msg = validar_conflictos_disponibilidad(
            usuario=self.user,
            sala=self.sala,
            dia_semana=lunes.weekday(),
            hora_inicio=time(9, 30),
            hora_fin=time(10, 30),
            fecha_inicio=lunes,
        )
        self.assertIsNotNone(msg)
        self.assertIn("Conflicto", msg)

    def test_reactivar_disponibilidad_inactiva(self):
        lunes = date.today() + timedelta(days=1)
        disp = DisponibilidadUsuario.objects.create(
            usuario=self.user,
            sala=self.sala,
            dia_semana=lunes.weekday(),
            hora_inicio=time(14, 0),
            hora_fin=time(15, 0),
            fecha_inicio=lunes,
            activa=False,
        )
        _, creado = _crear_o_reactivar_disponibilidad(
            self.user,
            self.sala,
            lunes.weekday(),
            time(14, 0),
            time(15, 0),
            lunes,
            None,
        )
        self.assertTrue(creado)
        disp.refresh_from_db()
        self.assertTrue(disp.activa)

    def test_slot_bloqueado(self):
        lunes = date.today() + timedelta(days=2)
        disp = DisponibilidadUsuario.objects.create(
            usuario=self.user,
            sala=self.sala,
            dia_semana=lunes.weekday(),
            hora_inicio=time(8, 0),
            hora_fin=time(9, 0),
            fecha_inicio=lunes,
        )
        BloqueoDisponibilidad.objects.create(
            disponibilidad=disp,
            fecha=lunes,
            hora_inicio=time(8, 0),
            hora_fin=time(9, 0),
            motivo="Mantenimiento",
        )
        self.assertTrue(
            _slot_bloqueado(disp, lunes, time(8, 0), time(9, 0))
        )
