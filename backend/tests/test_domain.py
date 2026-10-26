from datetime import datetime, timedelta, timezone

import pytest

from app.domain import Forecast, ForecastIndex, compute_metrics, quantile

T = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)


def _forecast(hours_before: float, mw: float, target: datetime = T) -> Forecast:
    return Forecast(target, target - timedelta(hours=hours_before), mw)


@pytest.fixture
def index() -> ForecastIndex:
    vintages = [_forecast(h, mw) for h, mw in [(30, 100), (10, 200), (4, 300), (1, 400), (-2, 999), (60, 999)]]
    return ForecastIndex(vintages, max_horizon=timedelta(hours=48))


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [(0, 400), (1, 400), (2, 300), (4, 300), (5, 200), (10, 200), (11, 100), (30, 100)],
)
def test_latest_respects_horizon(index, horizon, expected):
    assert index.latest(T, timedelta(hours=horizon)).mw == expected


def test_latest_ignores_post_target_and_beyond_max_horizon(index):
    assert index.latest(T, timedelta(hours=31)) is None
    assert index.latest(T + timedelta(hours=1), timedelta(0)) is None


def test_duplicate_publish_times_resolve_deterministically():
    idx = ForecastIndex([_forecast(4, 1), _forecast(2, 2)], timedelta(hours=48))
    assert idx.latest(T, timedelta(hours=3)).mw == 1


def test_metrics():
    m = compute_metrics([10, 20, 30, 40], [12, 18, 30, 50])
    assert m.count == 4
    assert m.mae == pytest.approx(3.5)
    assert m.bias == pytest.approx(-2.5)
    assert m.rmse == pytest.approx((4 + 4 + 0 + 100) ** 0.5 / 2)
    assert m.max_abs == 10
    assert m.nmae_pct == pytest.approx(14.0)


def test_metrics_empty_and_zero_mean():
    assert compute_metrics([], []) is None
    assert compute_metrics([0, 0], [1, -1]).nmae_pct is None


def test_quantile_interpolates():
    assert quantile([0, 10], 0.5) == 5
    assert quantile([1, 2, 3, 4, 5], 0.9) == pytest.approx(4.6)
