import base64
import hashlib
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def verify_django_pbkdf2(plain_password: str, hashed_password: str) -> bool:
    """Valida contraseñas con el formato estándar de Django (pbkdf2_sha256)."""
    try:
        parts = hashed_password.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt = parts[2]
            expected_hash = parts[3]
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("ascii"),
                iterations,
            )
            return base64.b64encode(dk).decode("ascii") == expected_hash
    except Exception:
        pass
    return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica contraseñas tanto en formato Argon2/bcrypt como Django PBKDF2."""
    if hashed_password and hashed_password.startswith("pbkdf2_sha256$"):
        return verify_django_pbkdf2(plain_password, hashed_password)
    try:
        return password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)