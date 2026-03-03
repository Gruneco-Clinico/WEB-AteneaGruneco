# -*- encoding: utf-8 -*-
"""
Signed token helpers for public patient endpoints.

Replaces raw ``paciente_id`` parameters in public URLs with HMAC-signed,
time-limited tokens using Django's ``signing`` module.

The token is signed with the project's ``SECRET_KEY``, so it cannot be
forged or tampered with.  Expiration is configurable via the
``PUBLIC_TOKEN_MAX_AGE`` setting (default: 72 hours = 259 200 seconds).

Usage
-----
Generate::

    from apps.home.tokens import generar_token_paciente
    token = generar_token_paciente(paciente.id)
    url = f"/guardar-examen-publico-epworth/?token={token}"

Validate::

    from apps.home.tokens import validar_token_paciente
    paciente_id = validar_token_paciente(token)
    if paciente_id is None:
        # Invalid or expired token
        ...
"""

import logging

from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

logger = logging.getLogger(__name__)

# Default: 72 hours (in seconds)
_DEFAULT_MAX_AGE = 72 * 60 * 60  # 259 200 s

# Namespace prefix prevents collision with other signed values
_SIGNER_SEP = ":"
_SIGNER_SALT = "atenea.public_exam_token"


def _get_max_age():
    """Return token lifetime in seconds from settings or default."""
    return getattr(settings, "PUBLIC_TOKEN_MAX_AGE", _DEFAULT_MAX_AGE)


def generar_token_paciente(paciente_id: int) -> str:
    """Return a signed, time-stamped token encoding *paciente_id*.

    The token is URL-safe and can be used as a query parameter.
    """
    signer = TimestampSigner(salt=_SIGNER_SALT)
    return signer.sign(str(paciente_id))


def validar_token_paciente(token: str) -> int | None:
    """Validate *token* and return the ``paciente_id`` it encodes.

    Returns ``None`` if the token is invalid, expired, or malformed.
    """
    if not token:
        return None

    signer = TimestampSigner(salt=_SIGNER_SALT)
    try:
        value = signer.unsign(token, max_age=_get_max_age())
        return int(value)
    except SignatureExpired:
        logger.warning("Token expirado: %s…", token[:20])
        return None
    except BadSignature:
        logger.warning("Token inválido (firma incorrecta): %s…", token[:20])
        return None
    except (ValueError, TypeError):
        logger.warning("Token con valor no numérico: %s…", token[:20])
        return None
