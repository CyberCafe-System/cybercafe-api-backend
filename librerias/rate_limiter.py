import os
import time
import math
import threading
from typing import Optional, Tuple
from fastapi import Request
from dotenv import load_dotenv

load_dotenv()


class LoginRateLimiter:
    """
    Controlador de límite de intentos para inicio de sesión en memoria y seguro para hilos.
    Permite bloquear temporalmente un usuario/IP si excede el número máximo de intentos fallidos.
    """

    def __init__(
        self,
        max_attempts: Optional[int] = None,
        lockout_seconds: Optional[int] = None,
    ):
        # Lee configuración de variables de entorno con valores por defecto
        if max_attempts is None:
            max_attempts = int(os.getenv("LOGIN_MAX_ATTEMPTS", "7"))
        if lockout_seconds is None:
            lockout_seconds = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "30"))

        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._records: dict[str, dict] = {}
        self._lock = threading.Lock()

    def get_client_key(self, request: Request, username: str) -> str:
        """
        Genera una clave única basada en la IP del cliente y el nombre de usuario.
        Evita bloqueos globales por DoS o afecciones a usuarios en la misma red.
        """
        client_ip = "127.0.0.1"
        if request.headers.get("x-forwarded-for"):
            # En caso de estar tras un proxy inverso (Nginx, Cloudflare, etc.)
            forwarded = request.headers.get("x-forwarded-for", "")
            client_ip = forwarded.split(",")[0].strip()
        elif request.client and request.client.host:
            client_ip = request.client.host

        clean_username = (username or "").strip().lower()
        return f"{client_ip}:{clean_username}"

    def is_locked(self, key: str) -> Tuple[bool, int]:
        """
        Verifica si una clave está actualmente bloqueada.
        Retorna (is_locked, remaining_seconds).
        """
        now = time.time()
        with self._lock:
            record = self._records.get(key)
            if not record:
                return False, 0

            locked_until = record.get("locked_until", 0)
            if locked_until > now:
                remaining = max(1, math.ceil(locked_until - now))
                return True, remaining

            # Si ya expiró el tiempo de bloqueo, reinicia los intentos
            if record.get("attempts", 0) >= self.max_attempts:
                self._records.pop(key, None)
            return False, 0

    def record_failure(self, key: str) -> Tuple[int, bool, int]:
        """
        Registra un intento fallido para la clave dada.
        Retorna (intentos_actuales, esta_bloqueado, segundos_restantes).
        """
        now = time.time()
        with self._lock:
            self._cleanup_stale_entries(now)

            record = self._records.setdefault(
                key,
                {"attempts": 0, "locked_until": 0, "last_attempt": now},
            )

            # Si el bloqueo previo ya pasó, resetea
            if record["locked_until"] > 0 and record["locked_until"] <= now:
                record["attempts"] = 0
                record["locked_until"] = 0

            record["attempts"] += 1
            record["last_attempt"] = now

            if record["attempts"] >= self.max_attempts:
                record["locked_until"] = now + self.lockout_seconds
                return record["attempts"], True, self.lockout_seconds

            return record["attempts"], False, 0

    def record_success(self, key: str) -> None:
        """
        Reinicia el contador de intentos ante un inicio de sesión exitoso.
        """
        with self._lock:
            self._records.pop(key, None)

    def reset_all(self) -> None:
        """
        Limpia todos los registros (útil para pruebas unitarias).
        """
        with self._lock:
            self._records.clear()

    def _cleanup_stale_entries(self, now: float) -> None:
        """
        Elimina entradas antiguas para evitar acumulación innecesaria en memoria.
        """
        # Solo limpia si hay más de 500 registros almacenados
        if len(self._records) < 500:
            return

        stale_threshold = max(self.lockout_seconds * 2, 300)
        keys_to_remove = [
            k
            for k, v in self._records.items()
            if (now - v.get("last_attempt", 0) > stale_threshold)
            and (v.get("locked_until", 0) <= now)
        ]
        for k in keys_to_remove:
            self._records.pop(k, None)


# Instancia compartida para la aplicación
login_rate_limiter = LoginRateLimiter()
