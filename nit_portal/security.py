from __future__ import annotations

from cryptography.fernet import Fernet

from .config import require_env


def get_credential_cipher() -> Fernet:
    return Fernet(require_env("CREDENTIALS_ENCRYPTION_KEY").encode("utf-8"))


def encrypt_secret(value: str) -> str:
    return get_credential_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return get_credential_cipher().decrypt(value.encode("utf-8")).decode("utf-8")
