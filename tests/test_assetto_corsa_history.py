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
from ac_race_engineer.telemetry.assetto_corsa.history import (
    AssettoCorsaHistoryService,
    format_time_ms,
)

NOW = datetime.now(
    timezone.utc
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

    session.add(
        SessionRecord(
            id="session-history",
            car_id=car.id,
            track_id=track.id,
            session_type="practice",
            source="assetto_corsa",
        )
    )

    session.flush()

    try:
        yield session

    finally:
        session.close()
        engine.dispose()


def add_lap(
    session: Session,
    *,
    lap_number: int,
    lap_time_ms: int,
) -> None:
    repository = LapRepository(
        session
    )

    repository.save(
        session_id="session-history",
        lap_number=lap_number,
        lap_time_ms=lap_time_ms,
        best_lap_time_ms=lap_time_ms,
        is_best=False,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=NOW,
    )


def add_sector(
    session: Session,
    *,
    lap_number: int,
    sector_number: int,
    sector_time_ms: int,
) -> None:
    repository = SectorRepository(
        session
    )

    repository.save(
        session_id="session-history",
        lap_number=lap_number,
        sector_index=(
            sector_number - 1
        ),
        sector_number=sector_number,
        sector_time_ms=sector_time_ms,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
        occurred_at=NOW,
    )


def test_format_time_ms() -> None:
    assert (
        format_time_ms(
            104532
        )
        == "1:44.532"
    )


def test_format_none() -> None:
    assert (
        format_time_ms(
            None
        )
        == "--:--.---"
    )


def test_history_finds_best_lap(
    database_session: Session,
) -> None:
    add_lap(
        database_session,
        lap_number=1,
        lap_time_ms=106000,
    )

    add_lap(
        database_session,
        lap_number=2,
        lap_time_ms=104532,
    )

    add_lap(
        database_session,
        lap_number=3,
        lap_time_ms=105100,
    )

    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    summary = service.get_summary(
        "session-history"
    )

    assert summary.lap_count == 3

    assert (
        summary.best_lap_number
        == 2
    )

    assert (
        summary.best_lap_time_ms
        == 104532
    )


def test_history_calculates_average(
    database_session: Session,
) -> None:
    add_lap(
        database_session,
        lap_number=1,
        lap_time_ms=100000,
    )

    add_lap(
        database_session,
        lap_number=2,
        lap_time_ms=102000,
    )

    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    summary = service.get_summary(
        "session-history"
    )

    assert (
        summary.average_lap_time_ms
        == pytest.approx(
            101000.0
        )
    )


def test_history_calculates_consistency(
    database_session: Session,
) -> None:
    add_lap(
        database_session,
        lap_number=1,
        lap_time_ms=100000,
    )

    add_lap(
        database_session,
        lap_number=2,
        lap_time_ms=102000,
    )

    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    summary = service.get_summary(
        "session-history"
    )

    assert (
        summary.consistency_stddev_ms
        == pytest.approx(
            1000.0
        )
    )


def test_history_builds_theoretical_best(
    database_session: Session,
) -> None:
    add_lap(
        database_session,
        lap_number=1,
        lap_time_ms=105000,
    )

    add_lap(
        database_session,
        lap_number=2,
        lap_time_ms=104500,
    )

    add_sector(
        database_session,
        lap_number=1,
        sector_number=1,
        sector_time_ms=34000,
    )

    add_sector(
        database_session,
        lap_number=1,
        sector_number=2,
        sector_time_ms=38000,
    )

    add_sector(
        database_session,
        lap_number=1,
        sector_number=3,
        sector_time_ms=33000,
    )

    add_sector(
        database_session,
        lap_number=2,
        sector_number=1,
        sector_time_ms=33500,
    )

    add_sector(
        database_session,
        lap_number=2,
        sector_number=2,
        sector_time_ms=37500,
    )

    add_sector(
        database_session,
        lap_number=2,
        sector_number=3,
        sector_time_ms=33500,
    )

    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    summary = service.get_summary(
        "session-history"
    )

    assert (
        summary.theoretical_best_lap_ms
        == 104000
    )

    assert (
        summary.potential_gain_ms
        == 500
    )

    assert [
        sector.sector_time_ms
        for sector in summary.best_sectors
    ] == [
        33500,
        37500,
        33000,
    ]


def test_history_groups_sectors_by_lap(
    database_session: Session,
) -> None:
    add_lap(
        database_session,
        lap_number=1,
        lap_time_ms=105000,
    )

    add_sector(
        database_session,
        lap_number=1,
        sector_number=2,
        sector_time_ms=38000,
    )

    add_sector(
        database_session,
        lap_number=1,
        sector_number=1,
        sector_time_ms=34000,
    )

    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    summary = service.get_summary(
        "session-history"
    )

    assert len(
        summary.laps
    ) == 1

    assert [
        sector.sector_number
        for sector in summary.laps[
            0
        ].sectors
    ] == [
        1,
        2,
    ]


def test_marks_session_best_lap(
    database_session: Session,
) -> None:
    add_lap(
        database_session,
        lap_number=1,
        lap_time_ms=106000,
    )

    add_lap(
        database_session,
        lap_number=2,
        lap_time_ms=104000,
    )

    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    summary = service.get_summary(
        "session-history"
    )

    best = next(
        lap
        for lap in summary.laps
        if lap.is_session_best
    )

    assert best.lap_number == 2


def test_missing_session_fails(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaHistoryService(
            database_session
        )
    )

    with pytest.raises(
        ValueError,
        match="Session not found",
    ):
        service.get_summary(
            "does-not-exist"
        )