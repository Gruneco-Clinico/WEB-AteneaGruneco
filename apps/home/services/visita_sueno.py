# -*- encoding: utf-8 -*-
"""
Resolución de visitas para el proyecto Caracterización del Sueño (portal público).

Prioridad:
  1. visita_id explícito (si pertenece al paciente y al proyecto sueño)
  2. Visita más reciente del proyecto con exámenes pendiente/en_progreso
  3. Visita más reciente del proyecto (fallback)
"""
from django.conf import settings

from ..models import Visita, VisitaExamen


def get_sueno_proyecto_id():
    return getattr(settings, "SUENO_PROYECTO_ID", 11)


def get_sueno_tipo_visita_ids():
    return getattr(settings, "SUENO_TIPO_VISITA_IDS", [20, 7])


def _visitas_sueno_qs(paciente):
    """Visitas del paciente vinculadas al proyecto sueño (excluye programadas)."""
    proyecto_id = get_sueno_proyecto_id()
    tipo_ids = get_sueno_tipo_visita_ids()
    return (
        Visita.objects.filter(paciente=paciente)
        .exclude(estado_visita="programada")
        .filter(
            models_q_or_proyecto(proyecto_id, tipo_ids)
        )
        .select_related("Tipo_visita", "Tipo_visita__proyecto")
        .order_by("-id")
    )


def models_q_or_proyecto(proyecto_id, tipo_ids):
    from django.db.models import Q

    q = Q(Tipo_visita__proyecto_id=proyecto_id)
    if tipo_ids:
        q |= Q(Tipo_visita_id__in=tipo_ids)
    return q


def resolver_visita_sueno(paciente, visita_id=None):
    """
    Devuelve la Visita objetivo para el portal público de sueño.

    Raises Visita.DoesNotExist si no hay visita válida.
    """
    if visita_id is not None:
        visita = (
            _visitas_sueno_qs(paciente)
            .filter(pk=int(visita_id))
            .first()
        )
        if visita:
            return visita
        raise Visita.DoesNotExist()

    qs = _visitas_sueno_qs(paciente)
    estados_abiertos = ("pendiente", "en_progreso")

    for visita in qs:
        if visita.visita_examenes.filter(estado__in=estados_abiertos).exists():
            return visita

    visita = qs.first()
    if visita:
        return visita
    raise Visita.DoesNotExist()


def resolver_visita_examen_publico(paciente, examen_id, visita_id=None):
    """
    Devuelve (visita, visita_examen) para un examen público del proyecto sueño.
    Crea VisitaExamen si no existe en la visita resuelta.
    """
    visita = resolver_visita_sueno(paciente, visita_id=visita_id)

    visita_examen = VisitaExamen.objects.filter(
        visita=visita, examen_id=examen_id
    ).first()

    if not visita_examen:
        from ..models import Examen

        examen = Examen.objects.get(pk=examen_id)
        visita_examen = VisitaExamen.objects.create(
            visita=visita, examen=examen, estado="pendiente"
        )

    return visita, visita_examen


def url_examen_publico(path, paciente_id, visita_id):
    """Construye URL pública con token y visita_id."""
    from ..tokens import generar_token_paciente

    token = generar_token_paciente(paciente_id)
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}token={token}&visita_id={visita_id}"
