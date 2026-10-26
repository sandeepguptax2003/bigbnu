from datetime import datetime

from pydantic import BaseModel

from .domain import Metrics
from .service import HorizonAccuracy, HourAccuracy, SeriesPoint


class MetaResponse(BaseModel):
    window_start: datetime
    window_end: datetime
    max_horizon_hours: int
    loaded_at: datetime
    actual_points: int
    forecast_targets: int


class SeriesResponse(BaseModel):
    start: datetime
    end: datetime
    horizon_hours: int
    points: list[SeriesPoint]
    metrics: Metrics | None


class AccuracyResponse(BaseModel):
    horizon_hours: int
    by_horizon: list[HorizonAccuracy]
    by_hour_of_day: list[HourAccuracy]
