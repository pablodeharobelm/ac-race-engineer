"""Versioned Kafka wire contract; payloads retain the existing telemetry models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ac_race_engineer.domain.session import SessionType
from ac_race_engineer.telemetry.models import TelemetryFrame


class KafkaTelemetryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    source: str = Field(min_length=1)
    session_type: SessionType = SessionType.TEST
    setup_id: str | None = None
    frame: TelemetryFrame

    def encode(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @property
    def key(self) -> bytes:
        # All samples of one session use the same Kafka partition.
        return self.frame.session_id.encode("utf-8")


