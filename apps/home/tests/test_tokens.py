# -*- encoding: utf-8 -*-
"""
Tests for apps.home.tokens — signed patient tokens for public endpoints.
"""

import time

from django.test import TestCase, override_settings
from django.core.signing import TimestampSigner

from apps.home.tokens import (
    generar_token_paciente,
    validar_token_paciente,
    _SIGNER_SALT,
)


class TokenGenerationTests(TestCase):
    """Tests for generar_token_paciente."""

    def test_generates_non_empty_string(self):
        token = generar_token_paciente(42)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_different_ids_produce_different_tokens(self):
        t1 = generar_token_paciente(1)
        t2 = generar_token_paciente(2)
        self.assertNotEqual(t1, t2)

    def test_token_is_url_safe(self):
        token = generar_token_paciente(999)
        # Should not contain characters that need URL encoding (except : which is allowed)
        for char in [" ", "\n", "\t", "<", ">", '"', "'", "&"]:
            self.assertNotIn(char, token)


class TokenValidationTests(TestCase):
    """Tests for validar_token_paciente."""

    def test_valid_token_returns_paciente_id(self):
        token = generar_token_paciente(123)
        result = validar_token_paciente(token)
        self.assertEqual(result, 123)

    def test_empty_token_returns_none(self):
        self.assertIsNone(validar_token_paciente(""))
        self.assertIsNone(validar_token_paciente(None))

    def test_garbage_token_returns_none(self):
        self.assertIsNone(validar_token_paciente("not-a-valid-token"))
        self.assertIsNone(validar_token_paciente("abc:def:ghi"))

    def test_tampered_token_returns_none(self):
        token = generar_token_paciente(42)
        tampered = token[:-3] + "XXX"
        self.assertIsNone(validar_token_paciente(tampered))

    @override_settings(PUBLIC_TOKEN_MAX_AGE=1)
    def test_expired_token_returns_none(self):
        """Token with 1-second max_age expires after sleeping."""
        token = generar_token_paciente(77)
        time.sleep(2)
        self.assertIsNone(validar_token_paciente(token))

    def test_wrong_salt_returns_none(self):
        """Token signed with a different salt should fail validation."""
        signer = TimestampSigner(salt="wrong-salt")
        bad_token = signer.sign("42")
        self.assertIsNone(validar_token_paciente(bad_token))

    def test_roundtrip_various_ids(self):
        """Multiple IDs roundtrip correctly."""
        for pid in [1, 100, 9999, 123456]:
            with self.subTest(pid=pid):
                token = generar_token_paciente(pid)
                self.assertEqual(validar_token_paciente(token), pid)


class TokenDefaultMaxAgeTests(TestCase):
    """Verify default max_age is 72 hours."""

    def test_token_valid_within_default_window(self):
        """A freshly-generated token should be valid (well within 72h)."""
        token = generar_token_paciente(1)
        self.assertEqual(validar_token_paciente(token), 1)
