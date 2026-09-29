from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import (
    CarRecord,
    SessionRecord,
    TrackRecord,
)
from ac_race_engineer.database.repositories.laps import (
    LapRepository,
)
from ac_race_engineer.database.repositories.sectors import (
    SectorRepository,
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
        name="Mazda MX-5 Cup",
    )

    track = TrackRecord(
        track_key="magione",
        name="Magione",
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


def test_save_lap(
    database_session: Session,
) -> None:
    repository = LapRepository(
        database_session
    )

    timestamp = datetime.now(
        timezone.utc
    )

    record = repository.save(
        session_id="session-001",
        lap_number=1,
        lap_time_ms=104532,
        best_lap_time_ms=104532,
        is_best=True,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=timestamp,
    )

    assert record.id is not None

    assert (
        record.session_id
        == "session-001"
    )

    assert record.lap_number == 1

    assert (
        record.lap_time_ms
        == 104532
    )

    assert record.is_best


def test_save_lap_is_idempotent(
    database_session: Session,
) -> None:
    repository = LapRepository(
        database_session
    )

    timestamp = datetime.now(
        timezone.utc
    )

    first = repository.save(
        session_id="session-001",
        lap_number=1,
        lap_time_ms=105000,
        best_lap_time_ms=105000,
        is_best=True,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=timestamp,
    )

    second = repository.save(
        session_id="session-001",
        lap_number=1,
        lap_time_ms=104500,
        best_lap_time_ms=104500,
        is_best=True,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=timestamp,
    )

    assert first.id == second.id

    assert (
        second.lap_time_ms
        == 104500
    )

    assert len(
        repository.list_for_session(
            "session-001"
        )
    ) == 1


def test_laps_are_ordered(
    database_session: Session,
) -> None:
    repository = LapRepository(
        database_session
    )

    timestamp = datetime.now(
        timezone.utc
    )

    for lap_number in (
        3,
        1,
        2,
    ):
        repository.save(
            session_id="session-001",
            lap_number=lap_number,
            lap_time_ms=105000,
            best_lap_time_ms=104000,
            is_best=False,
            position=1,
            is_in_pit=False,
            is_in_pit_lane=False,
            occurred_at=timestamp,
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


def test_save_sector(
    database_session: Session,
) -> None:
    repository = SectorRepository(
        database_session
    )

    timestamp = datetime.now(
        timezone.utc
    )

    record = repository.save(
        session_id="session-001",
        lap_number=1,
        sector_index=0,
        sector_number=1,
        sector_time_ms=33184,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=timestamp,
    )

    assert record.id is not None

    assert record.lap_number == 1
    assert record.sector_number == 1

    assert (
        record.sector_time_ms
        == 33184
    )


def test_sector_save_is_idempotent(
    database_session: Session,
) -> None:
    repository = SectorRepository(
        database_session
    )

    timestamp = datetime.now(
        timezone.utc
    )

    first = repository.save(
        session_id="session-001",
        lap_number=1,
        sector_index=0,
        sector_number=1,
        sector_time_ms=34000,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=timestamp,
    )

    second = repository.save(
        session_id="session-001",
        lap_number=1,
        sector_index=0,
        sector_number=1,
        sector_time_ms=33184,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=timestamp,
    )

    assert first.id == second.id

    assert (
        second.sector_time_ms
        == 33184
    )


def test_list_sectors_for_lap(
    database_session: Session,
) -> None:
    repository = SectorRepository(
        database_session
    )

    timestamp = datetime.now(
        timezone.utc
    )

    for sector_number in (
        3,
        1,
        2,
    ):
        repository.save(
            session_id="session-001",
            lap_number=1,
            sector_index=(
                sector_number - 1
            ),
            sector_number=sector_number,
            sector_time_ms=33000,
            position=1,
            is_in_pit=False,
            is_in_pit_lane=False,
            occurred_at=timestamp,
        )

    records = (
        repository.list_for_lap(
            session_id="session-001",
            lap_number=1,
        )
    )

    assert [
        record.sector_number
        for record in records
    ] == [
        1,
        2,
        3,
    ]