from datetime import datetime

from pydantic import BaseModel, Field

from ac_race_engineer.domain.session import SessionType


class LapEvent(BaseModel):
    timestamp: datetime

    session_id: str
    car_id: str
    track_id: str

    session_type: SessionType

    lap_number: int = Field(
        gt=0
    )

    lap_time_ms: int = Field(
        ge=0
    )

    best_lap_time_ms: int = Field(
        ge=0
    )

    is_best: bool

    position: int

    is_in_pit: bool
    is_in_pit_lane: bool


class SectorEvent(BaseModel):
    timestamp: datetime

    session_id: str
    car_id: str
    track_id: str

    session_type: SessionType

    lap_number: int = Field(
        gt=0
    )

    completed_laps: int = Field(
        ge=0
    )

    sector_index: int = Field(
        ge=0
    )

    sector_number: int = Field(
        gt=0
    )

    sector_time_ms: int = Field(
        ge=0
    )

    position: int

    is_in_pit: bool
    is_in_pit_lane: bool