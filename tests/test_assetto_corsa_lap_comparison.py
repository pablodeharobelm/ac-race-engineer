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
from ac_race_engineer.telemetry.assetto_corsa.comparison import (
    AssettoCorsaLapComparisonService,
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
            id="comparison-session",
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
        session_id="comparison-session",
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
        session_id="comparison-session",
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


def seed_two_laps(
    session: Session,
) -> None:
    add_lap(
        session,
        lap_number=1,
        lap_time_ms=105000,
    )

    add_lap(
        session,
        lap_number=2,
        lap_time_ms=104500,
    )

    add_sector(
        session,
        lap_number=1,
        sector_number=1,
        sector_time_ms=34000,
    )

    add_sector(
        session,
        lap_number=1,
        sector_number=2,
        sector_time_ms=38000,
    )

    add_sector(
        session,
        lap_number=1,
        sector_number=3,
        sector_time_ms=33000,
    )

    add_sector(
        session,
        lap_number=2,
        sector_number=1,
        sector_time_ms=33700,
    )

    add_sector(
        session,
        lap_number=2,
        sector_number=2,
        sector_time_ms=38400,
    )

    add_sector(
        session,
        lap_number=2,
        sector_number=3,
        sector_time_ms=32400,
    )


def test_compare_laps(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = service.compare(
        session_id="comparison-session",
        reference_lap_number=1,
        target_lap_number=2,
    )

    assert (
        comparison.total_delta_ms
        == -500
    )

    assert [
        sector.delta_ms
        for sector in comparison.sectors
    ] == [
        -300,
        400,
        -600,
    ]


def test_calculates_time_gained_and_lost(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = service.compare(
        session_id="comparison-session",
        reference_lap_number=1,
        target_lap_number=2,
    )

    assert (
        comparison.time_gained_ms
        == 900
    )

    assert (
        comparison.time_lost_ms
        == 400
    )


def test_detects_biggest_gain_and_loss(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = service.compare(
        session_id="comparison-session",
        reference_lap_number=1,
        target_lap_number=2,
    )

    assert (
        comparison.biggest_gain_sector
        == 3
    )

    assert (
        comparison.biggest_loss_sector
        == 2
    )


def test_sector_delta_matches_lap_delta(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = service.compare(
        session_id="comparison-session",
        reference_lap_number=1,
        target_lap_number=2,
    )

    assert (
        comparison.sector_delta_total_ms
        == -500
    )

    assert (
        comparison.sector_delta_total_ms
        == comparison.total_delta_ms
    )


def test_sector_comparison_is_complete(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = service.compare(
        session_id="comparison-session",
        reference_lap_number=1,
        target_lap_number=2,
    )

    assert (
        comparison.complete_sector_comparison
        is True
    )


def test_missing_sector_is_detected(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    repository = SectorRepository(
        database_session
    )

    sector = repository.get(
        session_id="comparison-session",
        lap_number=2,
        sector_number=3,
    )

    assert sector is not None

    database_session.delete(
        sector
    )

    database_session.flush()

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = service.compare(
        session_id="comparison-session",
        reference_lap_number=1,
        target_lap_number=2,
    )

    assert (
        comparison.complete_sector_comparison
        is False
    )

    assert len(
        comparison.sectors
    ) == 2


def test_same_lap_is_rejected(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        service.compare(
            session_id="comparison-session",
            reference_lap_number=1,
            target_lap_number=1,
        )


def test_missing_lap_is_rejected(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    with pytest.raises(
        ValueError,
        match="Lap not found",
    ):
        service.compare(
            session_id="comparison-session",
            reference_lap_number=1,
            target_lap_number=99,
        )


def test_compare_to_best(
    database_session: Session,
) -> None:
    seed_two_laps(
        database_session
    )

    service = (
        AssettoCorsaLapComparisonService(
            database_session
        )
    )

    comparison = (
        service.compare_to_best(
            session_id=(
                "comparison-session"
            ),
            lap_number=1,
        )
    )

    assert (
        comparison.reference_lap_number
        == 2
    )

    assert (
        comparison.target_lap_number
        == 1
    )

    assert (
        comparison.total_delta_ms
        == 500
    )