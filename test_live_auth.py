"""Targeted unit tests for DataLab-Live authentication hardening (PBKDF2-HMAC-SHA256)."""

from __future__ import annotations

import os
from unittest.mock import patch
import pytest

from datalab_live.api_client import is_backend_configured, make_api_request
from datalab_live.auth import (
    generate_password_hash,
    is_auth_configured,
    verify_credentials,
    verify_password_hash,
)


def test_generate_and_verify_password_hash():
    """Verify PBKDF2-HMAC-SHA256 derivation format and verification."""
    password = "SuperSecretPassword!42"
    stored_hash = generate_password_hash(password, iterations=100_000)

    # Must conform to pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    parts = stored_hash.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert parts[1] == "100000"
    assert len(parts[2]) == 32  # 16 bytes in hex = 32 chars
    assert len(parts[3]) == 64  # SHA-256 = 32 bytes = 64 hex chars

    # Valid password matches
    assert verify_password_hash(password, stored_hash) is True
    # Wrong password fails
    assert verify_password_hash("WrongPassword", stored_hash) is False


def test_verify_credentials_valid_hash():
    """Valid username + password against valid hash returns True."""
    username = "admin"
    password = "CorrectHorseBatteryStaple"
    stored_hash = generate_password_hash(password, iterations=100_000)

    assert verify_credentials(
        input_username=username,
        input_password=password,
        expected_username=username,
        expected_password_hash=stored_hash,
    ) is True


def test_verify_credentials_wrong_password():
    """Valid username + incorrect password returns False."""
    username = "admin"
    password = "CorrectHorseBatteryStaple"
    stored_hash = generate_password_hash(password, iterations=100_000)

    assert verify_credentials(
        input_username=username,
        input_password="IncorrectPassword",
        expected_username=username,
        expected_password_hash=stored_hash,
    ) is False


def test_verify_credentials_wrong_username():
    """Incorrect username returns False even with correct password."""
    username = "admin"
    password = "CorrectHorseBatteryStaple"
    stored_hash = generate_password_hash(password, iterations=100_000)

    assert verify_credentials(
        input_username="other_user",
        input_password=password,
        expected_username=username,
        expected_password_hash=stored_hash,
    ) is False


def test_verify_credentials_malformed_hash_fail_closed():
    """Malformed or tampered hash strings must fail closed (return False)."""
    username = "admin"
    password = "Password123"

    # Malformed strings
    malformed_hashes = [
        "not_a_valid_hash",
        "sha256$dummy",
        "pbkdf2_sha256$invalid_iterations$salt$hash",
        "pbkdf2_sha256$50000$salt$hash",  # iterations < 100k must be rejected
        "pbkdf2_sha256$100000$not_hex$hash",
        "md5$100000$salt$hash",
    ]

    for bad_hash in malformed_hashes:
        assert verify_credentials(
            input_username=username,
            input_password=password,
            expected_username=username,
            expected_password_hash=bad_hash,
        ) is False


def test_verify_credentials_empty_inputs_fail_closed():
    """Empty credentials must fail closed."""
    valid_hash = generate_password_hash("pwd", iterations=100_000)
    assert verify_credentials("", "pwd", "admin", valid_hash) is False
    assert verify_credentials("admin", "", "admin", valid_hash) is False
    assert verify_credentials("admin", "pwd", "", valid_hash) is False
    assert verify_credentials("admin", "pwd", "admin", "") is False


def test_is_auth_configured_fail_closed():
    """Fail closed when LIVE_USERNAME or LIVE_PASSWORD_HASH is absent or malformed."""
    valid_hash = generate_password_hash("pwd", iterations=100_000)

    with patch.dict(os.environ, {}, clear=True):
        assert is_auth_configured() is False

    with patch.dict(os.environ, {"LIVE_USERNAME": "admin"}, clear=True):
        assert is_auth_configured() is False

    with patch.dict(os.environ, {"LIVE_USERNAME": "admin", "LIVE_PASSWORD_HASH": "bad_format"}, clear=True):
        assert is_auth_configured() is False

    with patch.dict(
        os.environ,
        {"LIVE_USERNAME": "admin", "LIVE_PASSWORD_HASH": valid_hash},
        clear=True,
    ):
        assert is_auth_configured() is True


def test_is_backend_configured_fail_closed():
    """When backend URL or token is absent, client must report unconfigured."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_backend_configured() is False

    with patch.dict(
        os.environ,
        {"DATALAB_API_URL": "https://api.example.com"},
        clear=True,
    ):
        assert is_backend_configured() is False

    with patch.dict(
        os.environ,
        {
            "DATALAB_API_URL": "https://api.example.com",
            "DATALAB_API_TOKEN": "my-secret-token",
        },
        clear=True,
    ):
        assert is_backend_configured() is True


def test_make_api_request_missing_config():
    """make_api_request should return a clean error without crashing if config is missing."""
    with patch.dict(os.environ, {}, clear=True):
        data, err = make_api_request("/api/bench")
        assert data is None
        assert "Configuration manquante" in (err or "")
