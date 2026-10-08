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
    """Verifica contraseñas en formato Django PBKDF2, Django Argon2, y estándar."""
    if not hashed_password:
        return False
        
    # 1. Si es una contraseña antigua de Django (PBKDF2)
    if hashed_password.startswith("pbkdf2_sha256$"):
        return verify_django_pbkdf2(plain_password, hashed_password)
    
    # 2. Si es una contraseña Argon2 creada por Django
    clean_hash = hashed_password
    if hashed_password.startswith("argon2$"):
        # Cortamos "argon2" del inicio, dejando "$argon2id$v=19..." para pwdlib
        clean_hash = hashed_password[6:]
        
    # 3. Verificamos con pwdlib (cubriendo el Argon2 adaptado o hashes creados puramente en FastAPI)
    try:
        return password_hash.verify(plain_password, clean_hash)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Genera el hash con Argon2id y le agrega el prefijo de Django
    para que puedan iniciar sesión desde el panel de administración.
    """
    standard_hash = password_hash.hash(password)
    return f"argon2{standard_hash}"