# -*- encoding: utf-8 -*-
"""
Servicio de planes de visitas programadas (épica D).

Materializa visitas en estado ``programada`` sin VisitaExamen; al abrir
se crean los exámenes del snapshot de la serie.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.home.models import Examen, SerieVisitas, TipoVisita, Visita, VisitaExamen
from apps.home.models.patient import DatosDemograficos

MAX_FECHAS_SERIE = 24
TIPOS_FRECUENCIA = frozenset({"diario", "semanal", "lv", "custom"})
DIAS_LV = [0, 1, 2, 3, 4]  # lun–vie (Python weekday)


def _normalize_dias_semana(dias: Optional[Iterable]) -> List[int]:
    if not dias:
        return []
    clean: List[int] = []
    for d in dias:
        try:
            n = int(d)
        except (TypeError, ValueError):
            continue
        if 0 <= n <= 6 and n not in clean:
            clean.append(n)
    return clean


def _dias_permitidos(
    tipo: str, inicio: date, dias_semana: Optional[Sequence] = None
) -> Optional[set]:
    """
    Conjunto de weekdays permitidos, o None = todos (diario).
    """
    if tipo == "diario":
        return None
    if tipo == "semanal":
        return {inicio.weekday()}
    if tipo == "lv":
        return set(DIAS_LV)
    if tipo == "custom":
        dias = _normalize_dias_semana(dias_semana)
        if not dias:
            raise ValidationError(
                "Seleccione al menos un día de la semana para la frecuencia personalizada."
            )
        return set(dias)
    raise ValidationError(f"Tipo de frecuencia inválido: {tipo}.")


def generar_fechas(
    inicio: date,
    fin: date,
    tipo: str,
    dias_semana: Optional[Sequence] = None,
    *,
    max_fechas: int = MAX_FECHAS_SERIE,
) -> List[date]:
    """
    Genera fechas inclusivas según el preset de frecuencia.

    Tipos: diario | semanal | lv | custom.
    ``dias_semana``: enteros 0=lun … 6=dom (solo custom; lv usa L–V).
    """
    if fin < inicio:
        raise ValidationError("La fecha de fin debe ser mayor o igual a la de inicio.")
    if tipo not in TIPOS_FRECUENCIA:
        raise ValidationError(
            "Tipo de frecuencia inválido. Use diario, semanal, L-V o personalizado."
        )

    permitidos = _dias_permitidos(tipo, inicio, dias_semana)

    fechas: List[date] = []
    actual = inicio
    while actual <= fin and len(fechas) < max_fechas:
        if permitidos is None or actual.weekday() in permitidos:
            fechas.append(actual)
        actual = actual + timedelta(days=1)

    if not fechas:
        raise ValidationError(
            "El plan no genera ninguna fecha válida en el rango con esa frecuencia."
        )

    return fechas


def _normalize_examen_ids(examen_ids: Optional[Iterable]) -> List[int]:
    if not examen_ids:
        return []
    clean: List[int] = []
    for eid in examen_ids:
        if isinstance(eid, dict):
            eid = eid.get("id")
        try:
            clean.append(int(eid))
        except (TypeError, ValueError):
            continue
    return clean


def _paciente_en_proyecto(paciente: DatosDemograficos, tipo: TipoVisita) -> bool:
    if not tipo.proyecto_id:
        return False
    return paciente.proyectos.filter(pk=tipo.proyecto_id).exists()


def _dias_a_persistir(tipo: str, dias_semana: Optional[Sequence]) -> List[int]:
    if tipo == "lv":
        return list(DIAS_LV)
    if tipo == "custom":
        return _normalize_dias_semana(dias_semana)
    return []


@transaction.atomic
def crear_serie(
    *,
    paciente: DatosDemograficos,
    tipo_visita: TipoVisita,
    fecha_inicio: date,
    fecha_fin: date,
    frecuencia_unidad: str,
    dias_semana: Optional[Sequence] = None,
    evaluador: Optional[User] = None,
    examen_ids: Optional[Sequence] = None,
    frecuencia_cada: int = 1,
) -> Tuple[SerieVisitas, List[Visita], int]:
    """
    Crea la serie y visitas ``programada`` sin VisitaExamen.

    Omite fechas donde ya exista una Visita del mismo paciente+tipo+fecha.

    Returns:
        (serie, visitas_creadas, omitidas_por_duplicado)
    """
    if not _paciente_en_proyecto(paciente, tipo_visita):
        raise ValidationError(
            "El paciente no pertenece al proyecto del tipo de visita seleccionado."
        )

    fechas = generar_fechas(
        fecha_inicio, fecha_fin, frecuencia_unidad, dias_semana=dias_semana
    )
    dias_persist = _dias_a_persistir(frecuencia_unidad, dias_semana)

    clean_ids = _normalize_examen_ids(examen_ids)
    if not clean_ids:
        clean_ids = tipo_visita.iter_examen_ids()

    serie = SerieVisitas.objects.create(
        paciente=paciente,
        Tipo_visita=tipo_visita,
        evaluador=evaluador,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        frecuencia_unidad=frecuencia_unidad,
        frecuencia_cada=frecuencia_cada or 1,
        dias_semana=dias_persist,
        examenes=clean_ids,
        activa=True,
    )

    existentes = set(
        Visita.objects.filter(
            paciente=paciente,
            Tipo_visita=tipo_visita,
            fecha__in=fechas,
        ).values_list("fecha", flat=True)
    )

    creadas: List[Visita] = []
    omitidas = 0
    tipo_nombre = tipo_visita.nombre
    for f in fechas:
        if f in existentes:
            omitidas += 1
            continue
        visita = Visita.objects.create(
            paciente=paciente,
            nombre=f"{tipo_nombre} {f.isoformat()}",
            Tipo_visita=tipo_visita,
            serie=serie,
            fecha=f,
            evaluador=evaluador,
            estado_visita="programada",
        )
        creadas.append(visita)

    if not creadas and omitidas == len(fechas):
        serie.activa = False
        serie.save(update_fields=["activa"])

    return serie, creadas, omitidas


@transaction.atomic
def abrir_visita(visita: Visita) -> Visita:
    """Pasa una visita programada a abierta y crea VisitaExamen."""
    if visita.estado_visita != "programada":
        raise ValidationError(
            "Solo se pueden abrir visitas en estado programada."
        )
    if visita.firmado:
        raise ValidationError("No se puede abrir una visita firmada.")

    examen_ids: List[int] = []
    if visita.serie_id:
        examen_ids = visita.serie.iter_examen_ids()
    if not examen_ids and visita.Tipo_visita_id:
        examen_ids = visita.Tipo_visita.iter_examen_ids()

    visita.estado_visita = "abierta"
    visita.save()

    for eid in examen_ids:
        try:
            examen = Examen.objects.get(pk=eid)
        except Examen.DoesNotExist:
            continue
        VisitaExamen.objects.get_or_create(
            visita=visita,
            examen=examen,
            defaults={"estado": "pendiente"},
        )

    return visita


@transaction.atomic
def cancelar_resto_serie(serie: SerieVisitas) -> int:
    """
    Elimina visitas programadas no firmadas de la serie y la desactiva.

    No toca visitas abiertas ni cerradas. Returns count deleted.
    """
    qs = Visita.objects.filter(
        serie=serie,
        estado_visita="programada",
        firmado=False,
    )
    deleted, _ = qs.delete()
    serie.activa = False
    serie.save(update_fields=["activa"])
    return deleted
