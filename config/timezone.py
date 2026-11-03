import os
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone as dt_timezone,
    tzinfo,
)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv

load_dotenv()

ZONA_HORARIA_POR_DEFECTO = "America/El_Salvador"


def _cargar_zona(nombre: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(nombre)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _resolver_zona_horaria() -> tzinfo:
    nombre = os.getenv("TIMEZONE", ZONA_HORARIA_POR_DEFECTO).strip()
    if not nombre:
        nombre = ZONA_HORARIA_POR_DEFECTO

    zona = _cargar_zona(nombre)
    if zona is not None:
        return zona

    print(
        f"Aviso: TIMEZONE='{nombre}' no es válida. "
        f"Se usará {ZONA_HORARIA_POR_DEFECTO}."
    )
    zona = _cargar_zona(ZONA_HORARIA_POR_DEFECTO)
    if zona is not None:
        return zona

    print("Aviso: no se encontró la base de datos de zonas horarias. Se usará UTC-6.")
    return dt_timezone(timedelta(hours=-6))


ZONA_HORARIA = _resolver_zona_horaria()


def fecha_local_actual() -> date:
    return datetime.now(ZONA_HORARIA).date()


def rango_dia_utc(dia: date) -> tuple[datetime, datetime]:
    inicio_local = datetime.combine(dia, time.min, tzinfo=ZONA_HORARIA)
    fin_local = datetime.combine(
        dia + timedelta(days=1), time.min, tzinfo=ZONA_HORARIA
    )
    return inicio_local.astimezone(dt_timezone.utc), fin_local.astimezone(
        dt_timezone.utc
    )


def normalizar_a_zona_local(valor: datetime) -> datetime:
    if valor.tzinfo is None or valor.utcoffset() is None:
        return valor.replace(tzinfo=ZONA_HORARIA)
    return valor.astimezone(ZONA_HORARIA)


def normalizar_a_utc(valor: datetime) -> datetime:
    return normalizar_a_zona_local(valor).astimezone(dt_timezone.utc)
