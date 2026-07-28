from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken


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


def encrypt_secret(value: str, master_secret: str) -> str:
    if not value:
        return ""
    return _fernet(master_secret).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None, master_secret: str) -> str:
    if not value:
        return ""
    try:
        return _fernet(master_secret).decrypt(
            value.encode("ascii")
        ).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Encrypted platform secret cannot be decrypted") from exc


def mask_secret(value: str | None) -> str:
    if not value:
        return "Не задан"
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}••••••••{value[-4:]}"
