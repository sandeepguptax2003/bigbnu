import asyncio
import time
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from .config import Settings
from .domain import ForecastIndex, Metrics, compute_metrics
from .elexon import ElexonClient, UpstreamError


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    time: datetime
    actual: float | None
    forecast: float | None
    forecast_published: datetime | None


@dataclass(frozen=True, slots=True)
class HorizonAccuracy:
    horizon_hours: int
    metrics: Metrics | None


@dataclass(frozen=True, slots=True)
class HourAccuracy:
    hour: int
    metrics: Metrics | None


class Snapshot:
    def __init__(self, actuals: dict[datetime, float], index: ForecastIndex, loaded_at: datetime):
        self.actuals = actuals
        self.index = index
        self.loaded_at = loaded_at
        self.times = sorted(set(actuals) | set(index.targets))
        self.accuracy_by_horizon = lru_cache(maxsize=1)(self._accuracy_by_horizon)
        self.accuracy_by_hour = lru_cache(maxsize=64)(self._accuracy_by_hour)

    def _pairs(self, horizon_hours: int, targets: list[datetime]) -> tuple[list[float], list[float]]:
        horizon = timedelta(hours=horizon_hours)
        actual, forecast = [], []
        for target in targets:
            match = self.index.latest(target, horizon)
            if match is not None and target in self.actuals:
                actual.append(self.actuals[target])
                forecast.append(match.mw)
        return actual, forecast

    def series(self, start: datetime, end: datetime, horizon_hours: int) -> tuple[list[SeriesPoint], Metrics | None]:
        horizon = timedelta(hours=horizon_hours)
        times = self.times[bisect_left(self.times, start):bisect_left(self.times, end)]
        points = []
        for t in times:
            match = self.index.latest(t, horizon)
            points.append(SeriesPoint(t, self.actuals.get(t), match.mw if match else None, match.published if match else None))
        paired = [(p.actual, p.forecast) for p in points if p.actual is not None and p.forecast is not None]
        metrics = compute_metrics([a for a, _ in paired], [f for _, f in paired])
        return points, metrics

    def _accuracy_by_horizon(self, max_horizon_hours: int) -> list[HorizonAccuracy]:
        targets = self.index.targets
        return [HorizonAccuracy(h, compute_metrics(*self._pairs(h, targets))) for h in range(max_horizon_hours + 1)]

    def _accuracy_by_hour(self, horizon_hours: int) -> list[HourAccuracy]:
        by_hour: dict[int, list[datetime]] = {h: [] for h in range(24)}
        for target in self.index.targets:
            by_hour[target.hour].append(target)
        return [HourAccuracy(h, compute_metrics(*self._pairs(horizon_hours, ts))) for h, ts in by_hour.items()]


class DataStore:
    def __init__(self, settings: Settings, client: ElexonClient):
        self._settings = settings
        self._client = client
        self._snapshot: Snapshot | None = None
        self._expires_at = 0.0
        self._failed_until = 0.0
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        self._refresh_task: asyncio.Task | None = None

    def _loop_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock_loop is not loop:
            self._lock, self._lock_loop = asyncio.Lock(), loop
        return self._lock

    async def _load(self) -> Snapshot:
        actuals, forecasts = await self._client.load(self._settings.window_start, self._settings.window_end)
        index = ForecastIndex(forecasts, timedelta(hours=self._settings.max_horizon_hours))
        self._snapshot = Snapshot(actuals, index, datetime.now(timezone.utc))
        self._expires_at = time.monotonic() + self._settings.cache_ttl_seconds
        return self._snapshot

    async def _refresh_in_background(self) -> None:
        try:
            await self._load()
        except UpstreamError:
            self._expires_at = time.monotonic() + self._settings.stale_retry_seconds

    def _schedule_refresh(self) -> None:
        task = self._refresh_task
        if task is None or task.done() or task.get_loop() is not asyncio.get_running_loop():
            self._refresh_task = asyncio.create_task(self._refresh_in_background())

    async def snapshot(self) -> Snapshot:
        if self._snapshot is not None:
            if time.monotonic() >= self._expires_at:
                self._schedule_refresh()
            return self._snapshot
        async with self._loop_lock():
            if self._snapshot is not None:
                return self._snapshot
            if time.monotonic() < self._failed_until:
                raise UpstreamError("recent upstream failure")
            try:
                return await self._load()
            except UpstreamError:
                self._failed_until = time.monotonic() + self._settings.failure_backoff_seconds
                raise
