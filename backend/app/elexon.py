import asyncio
from datetime import datetime, timedelta

import httpx

from .config import Settings
from .domain import Forecast

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class UpstreamError(Exception):
    pass


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _chunks(start: datetime, end: datetime, days: int) -> list[tuple[datetime, datetime]]:
    step = timedelta(days=days)
    spans, cursor = [], start
    while cursor < end:
        spans.append((cursor, min(cursor + step, end)))
        cursor += step
    return spans


class ElexonClient:
    def __init__(self, settings: Settings, retry_backoff_seconds: float = 0.5):
        self._settings = settings
        self._backoff = retry_backoff_seconds

    async def load(self, start: datetime, end: datetime) -> tuple[dict[datetime, float], list[Forecast]]:
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.elexon_base_url,
                timeout=self._settings.http_timeout_seconds,
                transport=httpx.AsyncHTTPTransport(retries=2),
                headers={"Accept": "application/json"},
            ) as client:
                return await asyncio.gather(self.actuals(client, start, end), self.forecasts(client, start, end))
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise UpstreamError(str(exc)) from exc

    async def _get(self, client: httpx.AsyncClient, dataset: str, params: dict) -> list[dict]:
        for attempt in range(3):
            response = await client.get(f"/datasets/{dataset}/stream", params=params)
            if response.status_code not in RETRYABLE_STATUS or attempt == 2:
                break
            await asyncio.sleep(self._backoff * 2**attempt)
        response.raise_for_status()
        return response.json()

    async def actuals(self, client: httpx.AsyncClient, start: datetime, end: datetime) -> dict[datetime, float]:
        spans = _chunks(start - timedelta(days=1), end, self._settings.fetch_chunk_days)
        pages = await asyncio.gather(*(
            self._get(client, "FUELHH", {
                "settlementDateFrom": a.date().isoformat(),
                "settlementDateTo": b.date().isoformat(),
                "fuelType": "WIND",
            })
            for a, b in spans
        ))
        actuals = {}
        for row in (r for page in pages for r in page):
            target = _parse(row["startTime"])
            if start <= target < end and row.get("generation") is not None:
                actuals[target] = float(row["generation"])
        return actuals

    async def forecasts(self, client: httpx.AsyncClient, start: datetime, end: datetime) -> list[Forecast]:
        earliest = start - timedelta(hours=self._settings.max_horizon_hours)
        spans = _chunks(earliest, end, self._settings.fetch_chunk_days)
        pages = await asyncio.gather(*(
            self._get(client, "WINDFOR", {"publishDateTimeFrom": _iso(a), "publishDateTimeTo": _iso(b)})
            for a, b in spans
        ))
        unique = {}
        for row in (r for page in pages for r in page):
            if row.get("generation") is None:
                continue
            forecast = Forecast(_parse(row["startTime"]), _parse(row["publishTime"]), float(row["generation"]))
            if start <= forecast.target < end:
                unique[(forecast.target, forecast.published)] = forecast
        return list(unique.values())
