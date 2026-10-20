"""MFA con TOTP (HIPAA 164.312(d) — riesgo R-02).

El secreto TOTP se guarda CIFRADO (Fernet/AES-128, clave derivada de
SECRET_KEY) en la BD del tenant. El segundo factor se exige en cada inicio
de sesión una vez activado; los administradores están obligados a activarlo.
"""
import base64
import hashlib

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    raw = hashlib.sha256(settings.SECRET_KEY.encode() + b"|mfa-totp-v1").digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def new_secret():
    """Genera un secreto TOTP nuevo (base32)."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return ""


def provisioning_uri(secret: str, username: str, clinic: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=f"SecurePIP ({clinic})")


def verify_code(secret: str, code: str) -> bool:
    """Acepta el código actual ±30 s de tolerancia (relojes desfasados)."""
    code = (code or "").strip().replace(" ", "")
    if not secret or not code.isdigit():
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)
