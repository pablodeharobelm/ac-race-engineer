from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from ac_race_engineer.database.models import (
    CarRecord,
    LapRecord,
    LapTraceRecord,
    SectorRecord,
    SessionRecord,
    TrackRecord,
)
from ac_race_engineer.database.repositories.cars import (
    CarRepository,
)
from ac_race_engineer.database.repositories.lap_traces import (
    LapTraceRepository,
)
from ac_race_engineer.database.repositories.laps import (
    LapRepository,
)
from ac_race_engineer.database.repositories.sectors import (
    SectorRepository,
)
from ac_race_engineer.database.repositories.sessions import (
    SessionRepository,
)
from ac_race_engineer.database.repositories.tracks import (
    TrackRepository,
)
from ac_race_engineer.domain.session import (
    SessionMetadata,
)
from ac_race_engineer.storage.lap_trace import (
    LapTraceParquetStore,
)
from ac_race_engineer.telemetry.assetto_corsa.events import (
    LapEvent,
    SectorEvent,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_tracker import (
    LapTrace,
)


@dataclass(frozen=True)
class PersistenceDrainResult:
    sessions_saved: int
    laps_saved: int
    sectors_saved: int
    traces_saved: int


class AssettoCorsaPersistenceService:
    """
    Persist Assetto Corsa sessions, laps, sectors
    and dense lap traces.

    Relational metadata is stored in PostgreSQL.

    Dense driving trace samples are stored in
    Parquet through LapTraceParquetStore.

    This keeps SQLAlchemy concerns outside
    AssettoCorsaSource.
    """

    def __init__(
        self,
        session: Session,
        *,
        trace_store: (
            LapTraceParquetStore | None
        ) = None,
        trace_directory: str | Path = (
            "data/silver/lap_traces"
        ),
    ) -> None:
        self._session = session

        self.car_repository = (
            CarRepository(
                session
            )
        )

        self.track_repository = (
            TrackRepository(
                session
            )
        )

        self.session_repository = (
            SessionRepository(
                session
            )
        )

        self.lap_repository = (
            LapRepository(
                session
            )
        )

        self.sector_repository = (
            SectorRepository(
                session
            )
        )

        self.lap_trace_repository = (
            LapTraceRepository(
                session
            )
        )

        self.trace_store = (
            trace_store
            if trace_store is not None
            else LapTraceParquetStore(
                trace_directory
            )
        )

    def _get_or_create_car(
        self,
        car_key: str,
    ) -> CarRecord:
        record = (
            self.car_repository.get_by_key(
                car_key
            )
        )

        if record is not None:
            return record

        return self.car_repository.save(
            car_key=car_key,
            name=car_key,
        )

    def _get_or_create_track(
        self,
        track_key: str,
    ) -> TrackRecord:
        record = (
            self.track_repository.get_by_key(
                track_key
            )
        )

        if record is not None:
            return record

        return self.track_repository.save(
            track_key=track_key,
            name=track_key,
        )

    @staticmethod
    def _conditions(
        metadata: SessionMetadata,
    ) -> dict:
        return {
            "initial": {
                "air_temperature_c": (
                    metadata.initial_conditions.air_temperature_c
                ),
                "track_temperature_c": (
                    metadata.initial_conditions.track_temperature_c
                ),
                "grip_level": (
                    metadata.initial_conditions.grip_level
                ),
            },
            "final": {
                "air_temperature_c": (
                    metadata.final_conditions.air_temperature_c
                ),
                "track_temperature_c": (
                    metadata.final_conditions.track_temperature_c
                ),
                "grip_level": (
                    metadata.final_conditions.grip_level
                ),
            },
            "sample_count": (
                metadata.sample_count
            ),
            "duration_seconds": (
                metadata.duration_seconds
            ),
        }

    def _ensure_event_session(
        self,
        event: LapEvent | SectorEvent,
    ) -> SessionRecord:
        existing = (
            self.session_repository.get_by_id(
                event.session_id
            )
        )

        if existing is not None:
            return existing

        car = self._get_or_create_car(
            event.car_id
        )

        track = (
            self._get_or_create_track(
                event.track_id
            )
        )

        return self.session_repository.save(
            session_id=event.session_id,
            car_id=car.id,
            track_id=track.id,
            session_type=(
                event.session_type.value
            ),
            source="assetto_corsa",
            started_at=event.timestamp,
        )

    def _ensure_trace_session(
        self,
        trace: LapTrace,
    ) -> SessionRecord:
        existing = (
            self.session_repository.get_by_id(
                trace.session_id
            )
        )

        if existing is not None:
            return existing

        car = self._get_or_create_car(
            trace.car_id
        )

        track = (
            self._get_or_create_track(
                trace.track_id
            )
        )

        return self.session_repository.save(
            session_id=trace.session_id,
            car_id=car.id,
            track_id=track.id,
            session_type="test",
            source="assetto_corsa",
        )

    def save_completed_session(
        self,
        metadata: SessionMetadata,
    ) -> SessionRecord:
        car = self._get_or_create_car(
            metadata.car_id
        )

        track = (
            self._get_or_create_track(
                metadata.track_id
            )
        )

        return self.session_repository.save(
            session_id=(
                metadata.session_id
            ),
            car_id=car.id,
            track_id=track.id,
            session_type=(
                metadata.session_type.value
            ),
            source=metadata.source,
            started_at=(
                metadata.started_at
            ),
            ended_at=(
                metadata.ended_at
            ),
            conditions=(
                self._conditions(
                    metadata
                )
            ),
        )

    def save_lap_event(
        self,
        event: LapEvent,
    ) -> LapRecord:
        self._ensure_event_session(
            event
        )

        return self.lap_repository.save(
            session_id=event.session_id,
            lap_number=event.lap_number,
            lap_time_ms=event.lap_time_ms,
            best_lap_time_ms=(
                event.best_lap_time_ms
            ),
            is_best=event.is_best,
            position=event.position,
            is_in_pit=event.is_in_pit,
            is_in_pit_lane=(
                event.is_in_pit_lane
            ),
            occurred_at=event.timestamp,
        )

    def save_sector_event(
        self,
        event: SectorEvent,
    ) -> SectorRecord:
        self._ensure_event_session(
            event
        )

        return self.sector_repository.save(
            session_id=event.session_id,
            lap_number=event.lap_number,
            sector_index=(
                event.sector_index
            ),
            sector_number=(
                event.sector_number
            ),
            sector_time_ms=(
                event.sector_time_ms
            ),
            position=event.position,
            is_in_pit=event.is_in_pit,
            is_in_pit_lane=(
                event.is_in_pit_lane
            ),
            occurred_at=event.timestamp,
        )

    def save_lap_trace(
        self,
        trace: LapTrace,
    ) -> LapTraceRecord:
        self._ensure_trace_session(
            trace
        )

        parquet_file = (
            self.trace_store.write(
                trace
            )
        )

        first_sample = (
            trace.samples[0]
        )

        last_sample = (
            trace.samples[-1]
        )

        return self.lap_trace_repository.save(
            session_id=trace.session_id,
            lap_number=trace.lap_number,
            lap_time_ms=trace.lap_time_ms,
            sample_count=trace.sample_count,
            progress_start=(
                first_sample.progress
            ),
            progress_end=(
                last_sample.progress
            ),
            parquet_path=(
                parquet_file.as_posix()
            ),
            schema_version=(
                self.trace_store.SCHEMA_VERSION
            ),
        )

    def drain_source(
        self,
        source: AssettoCorsaSource,
    ) -> PersistenceDrainResult:
        sessions_saved = 0
        laps_saved = 0
        sectors_saved = 0
        traces_saved = 0

        while True:
            metadata = (
                source.pop_completed_session()
            )

            if metadata is None:
                break

            self.save_completed_session(
                metadata
            )

            sessions_saved += 1

        while True:
            event = (
                source.pop_lap_event()
            )

            if event is None:
                break

            self.save_lap_event(
                event
            )

            laps_saved += 1

        while True:
            event = (
                source.pop_sector_event()
            )

            if event is None:
                break

            self.save_sector_event(
                event
            )

            sectors_saved += 1

        while True:
            trace = (
                source.pop_lap_trace()
            )

            if trace is None:
                break

            self.save_lap_trace(
                trace
            )

            traces_saved += 1

        return PersistenceDrainResult(
            sessions_saved=(
                sessions_saved
            ),
            laps_saved=(
                laps_saved
            ),
            sectors_saved=(
                sectors_saved
            ),
            traces_saved=(
                traces_saved
            ),
        )