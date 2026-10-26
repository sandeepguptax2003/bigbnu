import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    elexon_base_url: str = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
    window_start: datetime = _utc(os.getenv("WINDOW_START", "2026-01-01T00:00:00Z"))
    window_end: datetime = _utc(os.getenv("WINDOW_END", "2026-02-01T00:00:00Z"))
    max_horizon_hours: int = int(os.getenv("MAX_HORIZON_HOURS", "48"))
    fetch_chunk_days: int = int(os.getenv("FETCH_CHUNK_DAYS", "7"))
    http_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "21600"))
    stale_retry_seconds: int = int(os.getenv("STALE_RETRY_SECONDS", "300"))
    failure_backoff_seconds: int = int(os.getenv("FAILURE_BACKOFF_SECONDS", "15"))
    cors_origins: list[str] = field(default_factory=lambda: _list(os.getenv("CORS_ORIGINS", "http://localhost:5173")))
    static_dir: str = os.getenv("STATIC_DIR", "")


settings = Settings()
