from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import (
    Base,
)
from ac_race_engineer.database.models import (
    LapTraceRecord,
    SessionRecord,
)
from ac_race_engineer.telemetry.assetto_corsa.capture_runner import (
    AssettoCorsaCaptureRunner,
)
from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.persistence import (
    AssettoCorsaPersistenceService,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


class TraceBackend(
    FakeAssettoCorsaBackend
):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.graphics_index = 0

        self.graphics_values = (
            (
                0,
                0.01,
                500,
            ),
            (
                0,
                0.50,
                50000,
            ),
            (
                0,
                0.98,
                99000,
            ),
            (
                1,
                0.01,
                500,
            ),
        )

    def read_graphics(
        self,
    ):
        original = (
            super().read_graphics()
        )

        index = min(
            self.graphics_index,
            len(
                self.graphics_values
            )
            - 1,
        )

        (
            completed_laps,
            progress,
            current_time_ms,
        ) = self.graphics_values[
            index
        ]

        self.graphics_index += 1

        return replace(
            original,
            completed_laps=completed_laps,
            normalized_car_position=progress,
            current_time_ms=current_time_ms,
            last_time_ms=100000,
        )


@pytest.fixture
def database_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    Base.metadata.create_all(
        engine
    )

    session = Session(
        engine
    )

    try:
        yield session

    finally:
        session.close()
        engine.dispose()


def test_capture_runner_reads_frames(
    database_session: Session,
    tmp_path: Path,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session,
            trace_directory=(
                tmp_path
                / "lap_traces"
            ),
        )
    )

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=persistence,
        sleep=lambda _: None,
    )

    result = runner.run(
        samples=5,
        interval_seconds=0.0,
    )

    assert (
        result.frames_read
        == 5
    )


def test_capture_runner_finishes_session(
    database_session: Session,
    tmp_path: Path,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session,
            trace_directory=(
                tmp_path
                / "lap_traces"
            ),
        )
    )

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=persistence,
        sleep=lambda _: None,
    )

    result = runner.run(
        samples=5,
        interval_seconds=0.0,
    )

    assert (
        result.sessions_saved
        == 1
    )

    assert (
        source.last_completed_session
        is not None
    )

    record = database_session.get(
        SessionRecord,
        (
            source
            .last_completed_session
            .session_id
        ),
    )

    assert record is not None

    assert (
        record.source
        == "assetto_corsa"
    )

    assert (
        record.session_type
        == "practice"
    )

    assert (
        record.ended_at
        is not None
    )


def test_capture_runner_calls_callback(
    database_session: Session,
    tmp_path: Path,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session,
            trace_directory=(
                tmp_path
                / "lap_traces"
            ),
        )
    )

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=persistence,
        sleep=lambda _: None,
    )

    speeds: list[float] = []

    runner.run(
        samples=3,
        interval_seconds=0.0,
        on_frame=lambda frame: (
            speeds.append(
                frame.vehicle.speed_kmh
            )
        ),
    )

    assert len(
        speeds
    ) == 3

    assert speeds == [
        143.2,
        143.2,
        143.2,
    ]


def test_capture_runner_persists_lap_trace(
    database_session: Session,
    tmp_path: Path,
) -> None:
    source = AssettoCorsaSource(
        TraceBackend(),
        stale_timeout_seconds=None,
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session,
            trace_directory=(
                tmp_path
                / "lap_traces"
            ),
        )
    )

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=persistence,
        sleep=lambda _: None,
    )

    result = runner.run(
        samples=4,
        interval_seconds=0.0,
    )

    assert (
        result.laps_saved
        == 1
    )

    assert (
        result.traces_saved
        == 1
    )

    records = (
        database_session.query(
            LapTraceRecord
        ).all()
    )

    assert len(
        records
    ) == 1

    record = records[0]

    assert (
        Path(
            record.parquet_path
        ).exists()
    )

    assert (
        record.sample_count
        == 3
    )


def test_capture_runner_rejects_invalid_samples(
    database_session: Session,
    tmp_path: Path,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session,
            trace_directory=(
                tmp_path
                / "lap_traces"
            ),
        )
    )

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=persistence,
    )

    with pytest.raises(
        ValueError,
        match="samples",
    ):
        runner.run(
            samples=0
        )


def test_capture_runner_rejects_negative_interval(
    database_session: Session,
    tmp_path: Path,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session,
            trace_directory=(
                tmp_path
                / "lap_traces"
            ),
        )
    )

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=persistence,
    )

    with pytest.raises(
        ValueError,
        match="interval_seconds",
    ):
        runner.run(
            samples=1,
            interval_seconds=-1.0,
        )

@pytest.mark.parametrize("interval", [float("nan"), float("inf"), -float("inf")])
def test_capture_rejects_non_finite_interval(database_session, tmp_path, interval):
    runner = AssettoCorsaCaptureRunner(
        source=AssettoCorsaSource(FakeAssettoCorsaBackend()),
        persistence=AssettoCorsaPersistenceService(
            database_session, trace_directory=tmp_path,
        ),
    )
    with pytest.raises(ValueError, match="finite"):
        runner.run(samples=1, interval_seconds=interval)


@pytest.mark.parametrize("failure", ["interrupt", "read_error"])
def test_capture_shutdown_on_interruption_and_read_error(database_session, tmp_path, failure):
    from ac_race_engineer.telemetry.assetto_corsa.exceptions import AssettoCorsaReadError

    error = KeyboardInterrupt if failure == "interrupt" else AssettoCorsaReadError
    source = AssettoCorsaSource(FakeAssettoCorsaBackend())

    def interrupt(_):
        raise error("capture stopped")

    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=AssettoCorsaPersistenceService(
            database_session, trace_directory=tmp_path, commit_on_drain=True,
        ),
        sleep=interrupt,
    )
    with pytest.raises(error):
        runner.run(samples=3)
    assert runner.statistics.frames_read == 1
    assert runner.statistics.sessions_saved == 1
    # Rollback must not erase the checkpoint saved before propagating the error.
    database_session.rollback()
    assert database_session.get(SessionRecord, source.last_completed_session.session_id) is not None
    assert runner.finish() == (0, 0, 0, 0)
    assert runner.statistics.sessions_saved == 1


def test_completed_lap_is_committed_before_capture_ends(database_session, tmp_path):
    source = AssettoCorsaSource(TraceBackend(), stale_timeout_seconds=None)
    runner = AssettoCorsaCaptureRunner(
        source=source,
        persistence=AssettoCorsaPersistenceService(
            database_session, trace_directory=tmp_path, commit_on_drain=True,
        ),
    )

    def check_checkpoint(frame):
        if runner.statistics.traces_saved:
            database_session.rollback()
            assert database_session.query(LapTraceRecord).count() == 1

    result = runner.run(samples=4, interval_seconds=0, on_frame=check_checkpoint)
    assert result.traces_saved == 1
