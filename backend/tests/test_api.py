from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.elexon import ElexonClient
from app.main import app
from app.service import DataStore

ACTUALS = [
    {"startTime": "2026-01-05T10:00:00Z", "generation": 1000},
    {"startTime": "2026-01-05T10:30:00Z", "generation": 1100},
    {"startTime": "2026-01-05T11:00:00Z", "generation": 1200},
]
FORECASTS = [
    {"startTime": "2026-01-05T10:00:00Z", "publishTime": "2026-01-05T04:30:00Z", "generation": 900},
    {"startTime": "2026-01-05T10:00:00Z", "publishTime": "2026-01-05T08:30:00Z", "generation": 1050},
    {"startTime": "2026-01-05T11:00:00Z", "publishTime": "2026-01-05T04:30:00Z", "generation": 1300},
]


def _mock_elexon(request: httpx.Request) -> httpx.Response:
    if "FUELHH" in request.url.path:
        assert request.url.params["fuelType"] == "WIND"
        return httpx.Response(200, json=ACTUALS)
    return httpx.Response(200, json=FORECASTS)


@pytest.fixture
def client(monkeypatch):
    real = httpx.AsyncClient

    def fake(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(_mock_elexon)
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake)
    monkeypatch.setattr(app.state, "store", DataStore(settings, ElexonClient(settings, retry_backoff_seconds=0)))
    with TestClient(app) as test_client:
        yield test_client


def test_series_picks_forecast_by_horizon(client):
    params = {"start": "2026-01-05T10:00:00Z", "end": "2026-01-05T12:00:00Z"}
    near = client.get("/api/series", params={**params, "horizon": 1}).json()
    far = client.get("/api/series", params={**params, "horizon": 4}).json()
    assert [p["forecast"] for p in near["points"]] == [1050, None, 1300]
    assert [p["forecast"] for p in far["points"]] == [900, None, 1300]
    assert near["metrics"]["count"] == 2
    assert near["metrics"]["mae"] == 75


def test_series_validation(client):
    assert client.get("/api/series", params={"start": "2026-01-02", "end": "2026-01-01"}).status_code == 422
    assert client.get("/api/series", params={"start": "2026-03-01", "end": "2026-03-02"}).status_code == 422
    assert client.get("/api/series", params={"start": "2026-01-01", "end": "2026-01-02", "horizon": 49}).status_code == 422


def test_accuracy_and_cache_headers(client):
    response = client.get("/api/accuracy", params={"horizon": 2})
    body = response.json()
    assert response.status_code == 200
    assert len(body["by_horizon"]) == 49 and len(body["by_hour_of_day"]) == 24
    assert "s-maxage" in response.headers["cache-control"]


def test_upstream_failure_returns_502(monkeypatch):
    real = httpx.AsyncClient

    def failing(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(lambda r: httpx.Response(503))
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", failing)
    monkeypatch.setattr(app.state, "store", DataStore(settings, ElexonClient(settings, retry_backoff_seconds=0)))
    with TestClient(app) as test_client:
        assert test_client.get("/api/meta").status_code == 502


def test_naive_datetimes_are_treated_as_utc(client):
    body = client.get("/api/series", params={"start": "2026-01-05T10:00:00", "end": "2026-01-05T11:00:00"}).json()
    assert datetime.fromisoformat(body["start"].replace("Z", "+00:00")) == datetime(2026, 1, 5, 10, tzinfo=timezone.utc)


def _client_with(monkeypatch, handler):
    real = httpx.AsyncClient

    def fake(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake)
    monkeypatch.setattr(app.state, "store", DataStore(settings, ElexonClient(settings, retry_backoff_seconds=0)))
    return TestClient(app)


def test_rate_limited_requests_are_retried(monkeypatch):
    seen = set()

    def flaky(request: httpx.Request) -> httpx.Response:
        if str(request.url) not in seen:
            seen.add(str(request.url))
            return httpx.Response(429)
        return _mock_elexon(request)

    with _client_with(monkeypatch, flaky) as test_client:
        assert test_client.get("/api/meta").status_code == 200


def test_malformed_upstream_payload_returns_502(monkeypatch):
    with _client_with(monkeypatch, lambda r: httpx.Response(200, json=[{"unexpected": 1}])) as test_client:
        assert test_client.get("/api/meta").status_code == 502


def test_docs_are_served(client):
    assert client.get("/openapi.json").status_code == 200
