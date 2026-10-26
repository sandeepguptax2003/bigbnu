from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .elexon import ElexonClient, UpstreamError
from .schemas import AccuracyResponse, MetaResponse, SeriesResponse
from .service import DataStore, Snapshot

CACHE_CONTROL = "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"


app = FastAPI(title="Wind Forecast Monitor API", version="1.0.0")
app.state.store = DataStore(settings, ElexonClient(settings))
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=["*"])


@app.exception_handler(UpstreamError)
async def upstream_error(_: Request, exc: UpstreamError):
    return JSONResponse(status_code=502, content={"detail": "Elexon BMRS is unavailable, please retry shortly."})


async def snapshot(request: Request) -> Snapshot:
    return await request.app.state.store.snapshot()


SnapshotDep = Annotated[Snapshot, Depends(snapshot)]
Horizon = Annotated[int, Query(ge=0, le=settings.max_horizon_hours, description="Forecast lead time in hours")]


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/meta", response_model=MetaResponse)
async def meta(data: SnapshotDep, response: Response):
    response.headers["Cache-Control"] = CACHE_CONTROL
    return MetaResponse(
        window_start=settings.window_start,
        window_end=settings.window_end,
        max_horizon_hours=settings.max_horizon_hours,
        loaded_at=data.loaded_at,
        actual_points=len(data.actuals),
        forecast_targets=len(data.index.targets),
    )


@app.get("/api/series", response_model=SeriesResponse)
async def series(data: SnapshotDep, response: Response, start: datetime, end: datetime, horizon: Horizon = 4):
    start, end = _utc(start), _utc(end)
    if start >= end:
        raise HTTPException(422, "start must be before end")
    start, end = max(start, settings.window_start), min(end, settings.window_end)
    if start >= end:
        raise HTTPException(422, "requested range is outside the available data window")
    points, metrics = data.series(start, end, horizon)
    response.headers["Cache-Control"] = CACHE_CONTROL
    return SeriesResponse(start=start, end=end, horizon_hours=horizon, points=points, metrics=metrics)


@app.get("/api/accuracy", response_model=AccuracyResponse)
async def accuracy(data: SnapshotDep, response: Response, horizon: Horizon = 4):
    response.headers["Cache-Control"] = CACHE_CONTROL
    return AccuracyResponse(
        horizon_hours=horizon,
        by_horizon=data.accuracy_by_horizon(settings.max_horizon_hours),
        by_hour_of_day=data.accuracy_by_hour(horizon),
    )


if settings.static_dir and Path(settings.static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")
