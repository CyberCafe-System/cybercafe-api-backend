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
    Permite bloquear temporalmente un usuario/IP si excede el número máximo de intentos fallidos,
    con incremento progresivo/exponencial del tiempo de espera en bloqueos consecutivos.
    """

    def __init__(
        self,
        max_attempts: Optional[int] = None,
        lockout_seconds: Optional[int] = None,
        max_lockout_seconds: Optional[int] = None,
        lockout_multiplier: Optional[float] = None,
        escalation_window: Optional[int] = None,
    ):
        # Lee configuración de variables de entorno con valores por defecto
        if max_attempts is None:
            max_attempts = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
        if lockout_seconds is None:
            lockout_seconds = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "120"))
        if max_lockout_seconds is None:
            max_lockout_seconds = int(os.getenv("LOGIN_MAX_LOCKOUT_SECONDS", "3600"))
        if lockout_multiplier is None:
            lockout_multiplier = float(os.getenv("LOGIN_LOCKOUT_MULTIPLIER", "2.0"))
        if escalation_window is None:
            escalation_window = int(os.getenv("LOGIN_ESCALATION_RESET_SECONDS", "1800"))

        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self.max_lockout_seconds = max_lockout_seconds
        self.lockout_multiplier = lockout_multiplier
        self.escalation_window = escalation_window
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

            # Si ya expiró el tiempo de bloqueo previo:
            # Reseteamos los intentos del ciclo para permitir un nuevo ciclo de intentos
            if record.get("attempts", 0) >= self.max_attempts:
                record["attempts"] = 0
                record["locked_until"] = 0

            # Si transcurrió la ventana de escalamiento sin actividad, resetea el nivel de penalización
            if now - record.get("last_attempt", 0) > self.escalation_window:
                record["lockout_count"] = 0

            return False, 0

    def record_failure(self, key: str) -> Tuple[int, bool, int]:
        """
        Registra un intento fallido para la clave dada.
        Si alcanza el límite de intentos, calcula el tiempo de espera con aumento progresivo.
        Retorna (intentos_actuales, esta_bloqueado, segundos_de_espera).
        """
        now = time.time()
        with self._lock:
            self._cleanup_stale_entries(now)

            record = self._records.setdefault(
                key,
                {
                    "attempts": 0,
                    "locked_until": 0,
                    "last_attempt": now,
                    "lockout_count": 0,
                },
            )

            # Si el bloqueo previo ya terminó, reset de intentos del ciclo
            if record["locked_until"] > 0 and record["locked_until"] <= now:
                record["attempts"] = 0
                record["locked_until"] = 0

            # Si pasó la ventana de escalamiento sin fallos, reiniciar conteo de bloqueos
            if now - record.get("last_attempt", 0) > self.escalation_window:
                record["lockout_count"] = 0

            record["attempts"] += 1
            record["last_attempt"] = now

            if record["attempts"] >= self.max_attempts:
                record["lockout_count"] = record.get("lockout_count", 0) + 1
                exponent = max(0, record["lockout_count"] - 1)
                wait_time = int(
                    min(
                        self.lockout_seconds * (self.lockout_multiplier ** exponent),
                        self.max_lockout_seconds,
                    )
                )
                record["locked_until"] = now + wait_time
                return record["attempts"], True, wait_time

            return record["attempts"], False, 0

    def record_success(self, key: str) -> None:
        """
        Reinicia completamente los intentos y el nivel de bloqueo ante un inicio de sesión exitoso.
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
        if len(self._records) < 500:
            return

        stale_threshold = max(self.escalation_window, 1800)
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
