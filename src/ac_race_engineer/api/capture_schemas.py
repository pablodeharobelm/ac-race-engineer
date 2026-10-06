from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ac_race_engineer.api.schemas import DrivingTraceSampleRequest


class CapturedSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    car_key: str
    track_key: str | None
    session_type: str
    source: str
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    lap_count: int
    trace_count: int


class CapturedLapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lap_number: int
    lap_time_ms: int
    is_best: bool
    sample_count: int
    trace_available: bool
    unavailable_reason: str | None


class CapturedTraceResponse(BaseModel):
    session_id: str
    lap_number: int
    lap_time_ms: int
    samples: list[DrivingTraceSampleRequest]


class StoredLapAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_lap_number: int = Field(gt=0)
    target_lap_number: int = Field(gt=0)
    grid_points: int = Field(default=201, ge=2, le=5001)
    explain: bool = False
    language: str = Field(default="es", min_length=1, max_length=16)
    persist: bool = True
