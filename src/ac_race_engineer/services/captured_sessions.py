"""Read captured sessions without exposing ORM sessions or storage paths to callers."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path

import pyarrow as pa
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ac_race_engineer.database.models import (
    CarRecord,
    LapRecord,
    LapTraceRecord,
    SessionRecord,
    TrackRecord,
)
from ac_race_engineer.database.repositories.lap_traces import LapTraceRepository
from ac_race_engineer.storage.lap_trace import LapTraceParquetStore
from ac_race_engineer.telemetry.assetto_corsa.trace_tracker import LapTrace


class CaptureNotFoundError(LookupError):
    """A requested session or lap is not present in the catalog."""


class TraceUnavailableError(RuntimeError):
    """A cataloged lap cannot be read or is inconsistent with its metadata."""


@dataclass(frozen=True)
class CapturedSession:
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


@dataclass(frozen=True)
class CapturedLap:
    lap_number: int
    lap_time_ms: int
    is_best: bool
    sample_count: int
    trace_available: bool
    unavailable_reason: str | None


class CapturedSessionService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_recent(self, *, limit: int = 20) -> list[CapturedSession]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        # Count in SQL rather than issuing one query per session.
        lap_counts = (
            select(LapRecord.session_id, func.count().label("count"))
            .group_by(LapRecord.session_id).subquery()
        )
        trace_counts = (
            select(LapTraceRecord.session_id, func.count().label("count"))
            .group_by(LapTraceRecord.session_id).subquery()
        )
        statement = (
            select(
                SessionRecord, CarRecord.car_key, TrackRecord.track_key,
                func.coalesce(lap_counts.c.count, 0),
                func.coalesce(trace_counts.c.count, 0),
            )
            .join(CarRecord, SessionRecord.car_id == CarRecord.id)
            .outerjoin(TrackRecord, SessionRecord.track_id == TrackRecord.id)
            .outerjoin(lap_counts, lap_counts.c.session_id == SessionRecord.id)
            .outerjoin(trace_counts, trace_counts.c.session_id == SessionRecord.id)
            .order_by(SessionRecord.created_at.desc(), SessionRecord.id.desc())
            .limit(limit)
        )
        with self._session_factory() as session:
            return [
                CapturedSession(
                    record.id, car, track, record.session_type, record.source,
                    record.started_at, record.ended_at, record.created_at, laps, traces,
                )
                for record, car, track, laps, traces in session.execute(statement)
            ]

    @staticmethod
    def _require_session(session: Session, session_id: str) -> SessionRecord:
        record = session.get(SessionRecord, session_id)
        if record is None:
            raise CaptureNotFoundError("Captured session not found")
        return record

    @staticmethod
    def _unavailable_reason(trace: LapTraceRecord | None) -> str | None:
        if trace is None:
            return "No complete driving trace was recorded for this lap"
        if trace.schema_version != LapTraceParquetStore.SCHEMA_VERSION:
            return "This driving trace uses an unsupported storage version"
        if trace.sample_count < 2:
            return "This driving trace has too few samples"
        if not Path(trace.parquet_path).is_file():
            return "The driving trace file is missing"
        return None

    def list_laps(self, session_id: str) -> list[CapturedLap]:
        with self._session_factory() as session:
            self._require_session(session, session_id)
            rows = list(session.execute(
                select(LapRecord, LapTraceRecord)
                .outerjoin(
                    LapTraceRecord,
                    (LapTraceRecord.session_id == LapRecord.session_id)
                    & (LapTraceRecord.lap_number == LapRecord.lap_number),
                )
                .where(LapRecord.session_id == session_id)
                .order_by(LapRecord.lap_number)
            ))
            valid_laps = [lap for lap, _ in rows if lap.lap_time_ms > 0]
            best = min(valid_laps, key=lambda lap: lap.lap_time_ms) if valid_laps else None
            result = []
            for lap, trace in rows:
                reason = self._unavailable_reason(trace)
                result.append(CapturedLap(
                    lap.lap_number, lap.lap_time_ms, best is not None and lap.id == best.id,
                    trace.sample_count if trace else 0,
                    reason is None, reason,
                ))
            return result

    def read_trace(self, session_id: str, lap_number: int) -> LapTrace:
        with self._session_factory() as session:
            captured_session = self._require_session(session, session_id)
            record = LapTraceRepository(session).get(
                session_id=session_id, lap_number=lap_number,
            )
            if record is None:
                lap = session.scalar(select(LapRecord).where(
                    LapRecord.session_id == session_id, LapRecord.lap_number == lap_number,
                ))
                if lap is None:
                    raise CaptureNotFoundError("Captured lap not found")
                raise TraceUnavailableError(self._unavailable_reason(None))
            reason = self._unavailable_reason(record)
            if reason:
                raise TraceUnavailableError(reason)
            try:
                trace = LapTraceParquetStore.read_file(Path(record.parquet_path))
            except (OSError, ValueError, TypeError, KeyError, pa.ArrowException) as exc:
                raise TraceUnavailableError("The driving trace file could not be read") from exc
            car = session.get(CarRecord, captured_session.car_id)
            track = (
                session.get(TrackRecord, captured_session.track_id)
                if captured_session.track_id is not None else None
            )
            if (
                trace.session_id != session_id or trace.lap_number != lap_number
                or trace.sample_count != record.sample_count
                or trace.lap_time_ms != record.lap_time_ms
                or car is None or trace.car_id != car.car_key
                or track is None or trace.track_id != track.track_key
            ):
                raise TraceUnavailableError("The driving trace does not match its session metadata")
            previous = None
            for sample in trace.samples:
                if (
                    not all(isfinite(value) for value in (
                        sample.progress, sample.elapsed_seconds, sample.speed_kmh,
                        sample.throttle, sample.brake, sample.steering_angle_deg,
                    ))
                    or not 0 <= sample.progress <= 1
                    or not 0 <= sample.throttle <= 1
                    or not 0 <= sample.brake <= 1
                    or (sample.clutch is not None and (not isfinite(sample.clutch) or not 0 <= sample.clutch <= 1))
                    or (sample.gear is not None and (type(sample.gear) is not int or not -1 <= sample.gear <= 10))
                    or sample.elapsed_seconds < 0 or sample.speed_kmh < 0
                    or (previous is not None and (
                        sample.progress <= previous.progress
                        or sample.elapsed_seconds < previous.elapsed_seconds
                    ))
                ):
                    raise TraceUnavailableError("The driving trace contains invalid telemetry samples")
                previous = sample
            return trace
