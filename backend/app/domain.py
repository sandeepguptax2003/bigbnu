import math
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class Forecast:
    target: datetime
    published: datetime
    mw: float


@dataclass(frozen=True, slots=True)
class Metrics:
    count: int
    mae: float
    rmse: float
    bias: float
    nmae_pct: float | None
    p50_abs: float
    p90_abs: float
    p99_abs: float
    max_abs: float
    p10_error: float


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    position = (len(sorted_values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def compute_metrics(actuals: list[float], forecasts: list[float]) -> Metrics | None:
    if not actuals:
        return None
    errors = [a - f for a, f in zip(actuals, forecasts)]
    absolute = sorted(abs(e) for e in errors)
    n = len(errors)
    mae = sum(absolute) / n
    mean_actual = sum(actuals) / n
    return Metrics(
        count=n,
        mae=mae,
        rmse=math.sqrt(sum(e * e for e in errors) / n),
        bias=sum(errors) / n,
        nmae_pct=100 * mae / mean_actual if mean_actual else None,
        p50_abs=quantile(absolute, 0.5),
        p90_abs=quantile(absolute, 0.9),
        p99_abs=quantile(absolute, 0.99),
        max_abs=absolute[-1],
        p10_error=quantile(sorted(errors), 0.1),
    )


class ForecastIndex:
    def __init__(self, forecasts: list[Forecast], max_horizon: timedelta):
        self._max_horizon = max_horizon
        grouped: dict[datetime, list[Forecast]] = defaultdict(list)
        for forecast in forecasts:
            lead = forecast.target - forecast.published
            if timedelta(0) <= lead <= max_horizon:
                grouped[forecast.target].append(forecast)
        self._published: dict[datetime, list[datetime]] = {}
        self._vintages: dict[datetime, list[Forecast]] = {}
        for target, items in grouped.items():
            items.sort(key=lambda f: f.published)
            self._vintages[target] = items
            self._published[target] = [f.published for f in items]
        self._targets = sorted(self._vintages)

    @property
    def targets(self) -> list[datetime]:
        return self._targets

    def latest(self, target: datetime, horizon: timedelta) -> Forecast | None:
        published = self._published.get(target)
        if not published:
            return None
        position = bisect_right(published, target - horizon)
        return self._vintages[target][position - 1] if position else None
