from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.auth import AuthConfigurationError, InvalidAccessToken, SupabaseJwtVerifier


ISSUER = "https://example.supabase.co/auth/v1"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeJwksClient:
    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        return SimpleNamespace(key=PRIVATE_KEY.public_key())


def signed_token(claims: dict[str, object]) -> str:
    return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-key"})


class SupabaseJwtVerifierTest(unittest.TestCase):
    def test_missing_supabase_url_raises_configuration_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AuthConfigurationError):
                SupabaseJwtVerifier.from_env()

    def test_allows_local_http_but_rejects_remote_http(self):
        verifier = SupabaseJwtVerifier("http://127.0.0.1:54321", FakeJwksClient())
        self.assertEqual(verifier.issuer, "http://127.0.0.1:54321/auth/v1")

        docker_verifier = SupabaseJwtVerifier(
            "http://host.docker.internal:54321",
            FakeJwksClient(),
        )
        self.assertEqual(
            docker_verifier.issuer,
            "http://host.docker.internal:54321/auth/v1",
        )

        with self.assertRaises(AuthConfigurationError):
            SupabaseJwtVerifier("http://example.com", FakeJwksClient())

    def test_uses_separate_issuer_for_docker_jwks_url(self):
        issuer = "http://127.0.0.1:54321/auth/v1"
        verifier = SupabaseJwtVerifier(
            "http://host.docker.internal:54321",
            FakeJwksClient(),
            issuer=issuer,
        )
        token = signed_token(
            {
                "sub": "user-123",
                "iss": issuer,
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            }
        )

        self.assertEqual(verifier.verify_access_token(token), "user-123")

    def test_rejects_remote_http_issuer(self):
        with self.assertRaises(AuthConfigurationError):
            SupabaseJwtVerifier(
                "http://host.docker.internal:54321",
                FakeJwksClient(),
                issuer="http://example.com/auth/v1",
            )

    def test_rejects_token_without_sub(self):
        verifier = SupabaseJwtVerifier("https://example.supabase.co", FakeJwksClient())
        token = signed_token(
            {
                "iss": ISSUER,
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            }
        )
        with self.assertRaises(InvalidAccessToken):
            verifier.verify_access_token(token)

    def test_returns_subject_for_valid_token(self):
        verifier = SupabaseJwtVerifier("https://example.supabase.co", FakeJwksClient())
        token = signed_token(
            {
                "sub": "user-123",
                "iss": ISSUER,
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            }
        )

        self.assertEqual(verifier.verify_access_token(token), "user-123")

    def test_rejects_expired_token(self):
        verifier = SupabaseJwtVerifier("https://example.supabase.co", FakeJwksClient())
        token = signed_token(
            {
                "sub": "user-123",
                "iss": ISSUER,
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            }
        )

        with self.assertRaises(InvalidAccessToken):
            verifier.verify_access_token(token)

    def test_rejects_wrong_issuer(self):
        verifier = SupabaseJwtVerifier("https://example.supabase.co", FakeJwksClient())
        token = signed_token(
            {
                "sub": "user-123",
                "iss": "https://attacker.example/auth/v1",
                "aud": "authenticated",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            }
        )

        with self.assertRaises(InvalidAccessToken):
            verifier.verify_access_token(token)
