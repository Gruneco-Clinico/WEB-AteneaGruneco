# -*- encoding: utf-8 -*-
"""
Cliente HTTP del endpoint RecuérdaMe ``POST /v1/integrations/atenea/activity``.

Devuelve el paquete users + login_logs + sessionGame para enriquecer cruces
clínicos en Atenea. Si falta configuración o la API falla, eleva
``RecuerdameActivityError`` con mensaje seguro para el dashboard.
"""
from __future__ import annotations

import logging
from datetime import date

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TIMEOUT = (5, 45)
CACHE_SEGUNDOS = 15 * 60
RUTA_ACTIVITY = "/v1/integrations/atenea/activity"
MENSAJE_ERROR = (
    "No fue posible consultar la actividad autenticada de RecuérdaMe. "
    "Revise la clave de integración o intente más tarde."
)


class RecuerdameActivityError(Exception):
    """Fallo al llamar al endpoint de actividad; ``str`` es seguro para UI."""


def _base_url():
    return (getattr(settings, "RECUERDAME_API_URL", "") or "").rstrip("/")


def _api_key():
    return (getattr(settings, "RECUERDAME_ATENEA_API_KEY", "") or "").strip()


def configurado():
    return bool(_base_url() and _api_key())


def consultar_actividad(emails, documents, date_from, date_to, include=None):
    """
    POST batch al endpoint de actividad.

    ``date_from`` / ``date_to``: ``date``, datetime o ``YYYY-MM-DD``.
    Retorna el dict JSON (``users``, ``not_found``, …).
    """
    if not configurado():
        raise RecuerdameActivityError(
            "Falta configurar RECUERDAME_API_URL o RECUERDAME_ATENEA_API_KEY."
        )

    emails = sorted({str(e).strip().lower() for e in (emails or []) if str(e).strip()})
    documents = sorted({str(d).strip() for d in (documents or []) if str(d).strip()})
    if not emails and not documents:
        return {
            "users": [],
            "not_found": {"emails": [], "documents": []},
            "users_count": 0,
        }

    from_s = _fecha_iso(date_from)
    to_s = _fecha_iso(date_to)
    include = include or ["logins", "sessions"]

    clave = (
        f"recuerdame_act:{from_s}:{to_s}:"
        f"{','.join(emails)}|{','.join(documents)}|{','.join(include)}"
    )
    en_cache = cache.get(clave)
    if en_cache is not None:
        return en_cache

    url = f"{_base_url()}{RUTA_ACTIVITY}"
    headers = {
        "Content-Type": "application/json",
        "X-Atenea-Api-Key": _api_key(),
    }
    cuerpo = {
        "emails": emails,
        "documents": documents,
        "from": from_s,
        "to": to_s,
        "include": include,
    }

    try:
        respuesta = requests.post(url, headers=headers, json=cuerpo, timeout=TIMEOUT)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.exceptions.RequestException as exc:
        estado = getattr(getattr(exc, "response", None), "status_code", None)
        logger.error(
            "Error al consultar actividad RecuérdaMe (HTTP %s): %s", estado, exc
        )
        raise RecuerdameActivityError(MENSAJE_ERROR) from None
    except ValueError:
        logger.error("Respuesta no JSON del endpoint de actividad RecuérdaMe.")
        raise RecuerdameActivityError(MENSAJE_ERROR) from None

    if not isinstance(datos, dict):
        raise RecuerdameActivityError(MENSAJE_ERROR)

    cache.set(clave, datos, CACHE_SEGUNDOS)
    return datos


def indice_por_email_y_documento(datos):
    """Índices ``email`` / ``document`` → fila de usuario del paquete."""
    por_email = {}
    por_documento = {}
    for user in (datos or {}).get("users") or []:
        if not isinstance(user, dict):
            continue
        email = str(user.get("email") or "").strip().lower()
        doc = str(user.get("document") or "").strip()
        if email and email not in por_email:
            por_email[email] = user
        if doc and doc not in por_documento:
            por_documento[doc] = user
    return por_email, por_documento


def _fecha_iso(valor):
    if isinstance(valor, date):
        return valor.isoformat()
    texto = str(valor or "").strip()
    return texto[:10] if texto else ""
