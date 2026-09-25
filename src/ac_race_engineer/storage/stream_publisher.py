"""Publish immutable Bronze microbatch files from an existing telemetry source."""

import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from ac_race_engineer.domain.session import SessionConditions, SessionMetadata, SessionType
from ac_race_engineer.lakehouse.bronze import BronzeTelemetryIngestor
from ac_race_engineer.telemetry.source import TelemetrySource


class TelemetryStreamPublisher:
    def __init__(
        self,
        source: TelemetrySource,
        output_directory: str | Path = "data/stream_input",
        *,
        session_type: SessionType = SessionType.TEST,
        setup_id: str | None = None,
    ):
        self.source = source
        self.output_directory = Path(output_directory)
        self.bronze = BronzeTelemetryIngestor(self.output_directory)
        self.session_type = session_type
        self.setup_id = setup_id
        self.session_identity = None

    def publish(self, sample_count: int = 20, *, sample_interval_seconds: float = 0.0) -> Path:
        if sample_count <= 0 or sample_interval_seconds < 0:
            raise ValueError("sample_count must be positive and sample interval non-negative")
        frames = []
        for index in range(sample_count):
            if index and sample_interval_seconds:
                time.sleep(sample_interval_seconds)
            frame = self.source.read_frame()
            identity = (frame.session_id, frame.car_id, frame.track_id)
            if self.session_identity is not None and identity != self.session_identity:
                raise ValueError("Telemetry source changed session, car or track while publishing")
            self.session_identity = identity
            frames.append(frame)
        first, last = frames[0], frames[-1]
        metadata = SessionMetadata(
            session_id=first.session_id,
            car_id=first.car_id,
            track_id=first.track_id,
            setup_id=self.setup_id,
            source=self.source.source_name,
            session_type=self.session_type,
            started_at=first.timestamp,
            ended_at=last.timestamp,
            sample_count=sample_count,
            duration_seconds=max(0.0, last.elapsed_seconds - first.elapsed_seconds),
            initial_conditions=SessionConditions(**first.environment.model_dump()),
            final_conditions=SessionConditions(**last.environment.model_dump()),
        )
        destination = self.output_directory / f"batch-{uuid4().hex}.parquet"
        temporary = destination.with_name("." + destination.name + ".tmp")
        ingested_at = datetime.now(UTC)
        rows = [
            self.bronze._flatten_frame(frame, metadata, destination, ingested_at)
            for frame in frames
        ]
        try:
            pq.write_table(pa.Table.from_pylist(rows), temporary, compression="snappy")
            # Rename on the same filesystem: the file source never sees partial files.
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination


