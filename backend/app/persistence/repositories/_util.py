from datetime import UTC, datetime


def dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def str_to_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
