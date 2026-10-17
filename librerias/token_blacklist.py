import time
from datetime import datetime, timezone
import threading
from typing import Dict, List, Optional


class TokenBlacklist:
    """
    Gestor en memoria y seguro para hilos de tokens JWT revocados (Blacklist).
    Invalida de inmediato los tokens cuyos usuarios hayan cerrado sesión explícitamente.
    """

    def __init__(self):
        # Mapeo: { token_str: dict con metadata y expiracion }
        self._blacklist: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def revocar_token(
        self,
        token: str,
        exp_timestamp: float,
        info_usuario: Optional[dict] = None,
    ) -> None:
        """
        Registra un token en la lista de revocados junto con su tiempo de expiración y datos del usuario.
        """
        now = time.time()
        with self._lock:
            self._cleanup_stale_tokens(now)

            if not exp_timestamp or exp_timestamp <= 0:
                exp_timestamp = now + 7200

            metadata = info_usuario or {}
            self._blacklist[token] = {
                "exp": exp_timestamp,
                "revocado_en": now,
                "username": metadata.get("username", "Desconocido"),
                "usuario_id": metadata.get("id"),
                "id_rol": metadata.get("id_rol"),
            }

    def esta_revocado(self, token: str) -> bool:
        """
        Comprueba si un token se encuentra en la lista negra y aún no ha alcanzado
        su expiración natural.
        """
        now = time.time()
        with self._lock:
            record = self._blacklist.get(token)
            if not record:
                return False

            exp = record.get("exp", 0) if isinstance(record, dict) else record
            if exp <= now:
                self._blacklist.pop(token, None)
                return False

            return True

    def listar_tokens_revocados(self) -> List[dict]:
        """
        Retorna la lista de todos los tokens actualmente revocados con información legible.
        """
        now = time.time()
        resultados = []
        with self._lock:
            # Lista temporal de tokens a depurar si ya expiraron
            expirados = []
            for token, data in self._blacklist.items():
                exp = data.get("exp", 0) if isinstance(data, dict) else data
                if exp <= now:
                    expirados.append(token)
                    continue

                revocado_en_ts = data.get("revocado_en", now) if isinstance(data, dict) else now
                revocado_en_str = datetime.fromtimestamp(revocado_en_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                expira_en_str = datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                resultados.append({
                    "token_resumido": f"{token[:15]}...{token[-10:]}" if len(token) > 25 else token,
                    "token_completo": token,
                    "username": data.get("username", "Desconocido") if isinstance(data, dict) else "Desconocido",
                    "usuario_id": data.get("usuario_id") if isinstance(data, dict) else None,
                    "id_rol": data.get("id_rol") if isinstance(data, dict) else None,
                    "revocado_en": revocado_en_str,
                    "expira_en": expira_en_str,
                    "segundos_restantes": max(0, int(exp - now)),
                })

            for t in expirados:
                self._blacklist.pop(t, None)

        return resultados

    def reset_all(self) -> None:
        """
        Limpia toda la lista negra (útil para pruebas unitarias).
        """
        with self._lock:
            self._blacklist.clear()

    def _cleanup_stale_tokens(self, now: float) -> None:
        """
        Elimina tokens cuya expiración ya ocurrió para mantener bajo el uso de memoria.
        """
        if len(self._blacklist) < 100:
            return

        caducados = [
            t
            for t, data in self._blacklist.items()
            if (data.get("exp", 0) if isinstance(data, dict) else data) <= now
        ]
        for t in caducados:
            self._blacklist.pop(t, None)


# Instancia compartida para la aplicación
token_blacklist = TokenBlacklist()
