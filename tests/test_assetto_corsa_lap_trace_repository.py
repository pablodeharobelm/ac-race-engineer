import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import (
    CarRecord,
    LapTraceRecord,
    SessionRecord,
    TrackRecord,
)
from ac_race_engineer.database.repositories.lap_traces import (
    LapTraceRepository,
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

    car = CarRecord(
        car_key="ks_mazda_mx5_cup",
        name="ks_mazda_mx5_cup",
    )

    track = TrackRecord(
        track_key="magione",
        name="magione",
    )

    session.add_all(
        [
            car,
            track,
        ]
    )

    session.flush()

    session_record = SessionRecord(
        id="session-001",
        car_id=car.id,
        track_id=track.id,
        session_type="practice",
        source="assetto_corsa",
    )

    session.add(
        session_record
    )

    session.flush()

    try:
        yield session

    finally:
        session.close()
        engine.dispose()


def test_saves_lap_trace_metadata(
    database_session: Session,
) -> None:
    repository = LapTraceRepository(
        database_session
    )

    record = repository.save(
        session_id="session-001",
        lap_number=1,
        lap_time_ms=100000,
        sample_count=2000,
        progress_start=0.01,
        progress_end=0.99,
        parquet_path=(
            "data/silver/lap_traces/"
            "session_id=session-001/"
            "lap_number=0001/"
            "trace.parquet"
        ),
        schema_version=1,
    )

    assert record.id is not None

    stored = database_session.get(
        LapTraceRecord,
        record.id,
    )

    assert stored is not None

    assert stored.session_id == (
        "session-001"
    )

    assert stored.lap_number == 1

    assert (
        stored.sample_count
        == 2000
    )

    assert (
        stored.lap_time_ms
        == 100000
    )


def test_get_returns_trace_metadata(
    database_session: Session,
) -> None:
    repository = LapTraceRepository(
        database_session
    )

    repository.save(
        session_id="session-001",
        lap_number=2,
        lap_time_ms=99500,
        sample_count=1980,
        progress_start=0.01,
        progress_end=0.99,
        parquet_path="lap2.parquet",
        schema_version=1,
    )

    record = repository.get(
        session_id="session-001",
        lap_number=2,
    )

    assert record is not None

    assert (
        record.parquet_path
        == "lap2.parquet"
    )


def test_get_returns_none_when_missing(
    database_session: Session,
) -> None:
    repository = LapTraceRepository(
        database_session
    )

    record = repository.get(
        session_id="session-001",
        lap_number=99,
    )

    assert record is None


def test_save_is_upsert(
    database_session: Session,
) -> None:
    repository = LapTraceRepository(
        database_session
    )

    first = repository.save(
        session_id="session-001",
        lap_number=1,
        lap_time_ms=100000,
        sample_count=2000,
        progress_start=0.01,
        progress_end=0.98,
        parquet_path="old.parquet",
        schema_version=1,
    )

    second = repository.save(
        session_id="session-001",
        lap_number=1,
        lap_time_ms=99500,
        sample_count=2100,
        progress_start=0.005,
        progress_end=0.995,
        parquet_path="new.parquet",
        schema_version=1,
    )

    assert first.id == second.id

    assert (
        second.lap_time_ms
        == 99500
    )

    assert (
        second.sample_count
        == 2100
    )

    assert (
        second.parquet_path
        == "new.parquet"
    )

    records = (
        repository.list_for_session(
            "session-001"
        )
    )

    assert len(
        records
    ) == 1


def test_lists_traces_in_lap_order(
    database_session: Session,
) -> None:
    repository = LapTraceRepository(
        database_session
    )

    for lap_number in (
        3,
        1,
        2,
    ):
        repository.save(
            session_id="session-001",
            lap_number=lap_number,
            lap_time_ms=100000,
            sample_count=2000,
            progress_start=0.01,
            progress_end=0.99,
            parquet_path=(
                f"lap-{lap_number}.parquet"
            ),
            schema_version=1,
        )

    records = (
        repository.list_for_session(
            "session-001"
        )
    )

    assert [
        record.lap_number
        for record in records
    ] == [
        1,
        2,
        3,
    ]