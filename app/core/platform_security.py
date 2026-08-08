from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken


PLATFORM_SECRET_VERSION = "v2:"
PLATFORM_ENCRYPTION_SECRET_ENV = "PLATFORM_ENCRYPTION_SECRET"
MIN_PLATFORM_ENCRYPTION_SECRET_LENGTH = 32


def hash_password(password: str, *, iterations: int = 310_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        salt = base64.urlsafe_b64decode(raw_salt.encode("ascii"))
        expected = base64.urlsafe_b64decode(raw_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def _fernet(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(
        hashlib.sha256(secret.encode("utf-8")).digest()
    )
    return Fernet(key)


def platform_encryption_secret() -> str:
    return os.getenv(PLATFORM_ENCRYPTION_SECRET_ENV, "").strip()


def validate_platform_encryption_secret(secret: str) -> None:
    if not secret:
        return
    if len(secret) < MIN_PLATFORM_ENCRYPTION_SECRET_LENGTH:
        raise RuntimeError(
            f"{PLATFORM_ENCRYPTION_SECRET_ENV} must be at least "
            f"{MIN_PLATFORM_ENCRYPTION_SECRET_LENGTH} characters"
        )


def encrypt_secret(value: str, master_secret: str) -> str:
    """Encrypt a platform credential with backward-compatible key versioning.

    Legacy ciphertext has no prefix and remains encrypted with WEB_ADMIN_SECRET.
    Once PLATFORM_ENCRYPTION_SECRET is configured, all new ciphertext is written
    as v2 and no longer depends on the admin-session signing secret.
    """
    if not value:
        return ""
    dedicated = platform_encryption_secret()
    if dedicated:
        validate_platform_encryption_secret(dedicated)
        payload = _fernet(dedicated).encrypt(value.encode("utf-8")).decode("ascii")
        return PLATFORM_SECRET_VERSION + payload
    return _fernet(master_secret).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None, master_secret: str) -> str:
    if not value:
        return ""
    try:
        if value.startswith(PLATFORM_SECRET_VERSION):
            dedicated = platform_encryption_secret()
            if not dedicated:
                raise RuntimeError(
                    f"{PLATFORM_ENCRYPTION_SECRET_ENV} is required to decrypt v2 platform secrets"
                )
            validate_platform_encryption_secret(dedicated)
            payload = value[len(PLATFORM_SECRET_VERSION):]
            return _fernet(dedicated).decrypt(payload.encode("ascii")).decode("utf-8")
        # Unprefixed ciphertext is the legacy format and intentionally remains
        # tied to the old WEB_ADMIN_SECRET until scripts.rekey_platform_secrets
        # converts it to v2.
        return _fernet(master_secret).decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Encrypted platform secret cannot be decrypted") from exc


def mask_secret(value: str | None) -> str:
    if not value:
        return "Не задан"
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}••••••••{value[-4:]}"
