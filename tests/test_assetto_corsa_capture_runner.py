import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import (
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
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session
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

    assert result.frames_read == 5


def test_capture_runner_finishes_session(
    database_session: Session,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session
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

    record = database_session.get(
        SessionRecord,
        source.last_completed_session.session_id,
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
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session
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

    assert len(speeds) == 3

    assert speeds == [
        143.2,
        143.2,
        143.2,
    ]


def test_capture_runner_rejects_invalid_samples(
    database_session: Session,
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session
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
) -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    persistence = (
        AssettoCorsaPersistenceService(
            database_session
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