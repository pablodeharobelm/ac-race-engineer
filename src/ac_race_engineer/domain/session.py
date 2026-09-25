from datetime import datetime

from pydantic import BaseModel, Field

from ac_race_engineer.compat import StrEnum


class SessionType(StrEnum):
    PRACTICE = "practice"
    QUALIFYING = "qualifying"
    RACE = "race"
    HOTLAP = "hotlap"
    TEST = "test"


class SessionConditions(BaseModel):
    air_temperature_c: float
    track_temperature_c: float

    grip_level: float = Field(
        ge=0.0,
        le=1.0,
    )


class SessionMetadata(BaseModel):
    session_id: str

    car_id: str
    track_id: str

    setup_id: str | None = None

    source: str
    session_type: SessionType

    started_at: datetime
    ended_at: datetime

    sample_count: int = Field(
        gt=0
    )

    duration_seconds: float = Field(
        ge=0.0
    )

    initial_conditions: SessionConditions
    final_conditions: SessionConditions

