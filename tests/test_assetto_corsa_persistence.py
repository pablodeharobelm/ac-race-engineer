from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import (
    LapRecord,
    SectorRecord,
    SessionRecord,
)
from ac_race_engineer.domain.session import (
    SessionConditions,
    SessionMetadata,
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.events import (
    LapEvent,
    SectorEvent,
)
from ac_race_engineer.telemetry.assetto_corsa.persistence import (
    AssettoCorsaPersistenceService,
)

NOW = datetime(
    2026,
    9,
    28,
    18,
    0,
    tzinfo=timezone.utc,
)


@pytest.fixture
def database_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )

    @event.listens_for(
        engine,
        "connect",
    )
    def enable_foreign_keys(
        dbapi_connection,
        connection_record,
    ) -> None:
        del connection_record

        cursor = (
            dbapi_connection.cursor()
        )

        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )

        cursor.close()

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


def build_lap_event() -> LapEvent:
    return LapEvent(
        timestamp=NOW,
        session_id="ac-session-001",
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        session_type=(
            SessionType.PRACTICE
        ),
        lap_number=1,
        lap_time_ms=104532,
        best_lap_time_ms=104532,
        is_best=True,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
    )


def build_sector_event() -> SectorEvent:
    return SectorEvent(
        timestamp=NOW,
        session_id="ac-session-001",
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        session_type=(
            SessionType.PRACTICE
        ),
        lap_number=1,
        completed_laps=0,
        sector_index=0,
        sector_number=1,
        sector_time_ms=33184,
        position=1,
        is_in_pit=False,
        is_in_pit_lane=False,
    )


def build_metadata() -> SessionMetadata:
    return SessionMetadata(
        session_id="ac-session-001",
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        source="assetto_corsa",
        session_type=(
            SessionType.PRACTICE
        ),
        started_at=NOW,
        ended_at=(
            NOW
            + timedelta(
                minutes=10
            )
        ),
        sample_count=12000,
        duration_seconds=600.0,
        initial_conditions=(
            SessionConditions(
                air_temperature_c=24.0,
                track_temperature_c=31.0,
                grip_level=0.97,
            )
        ),
        final_conditions=(
            SessionConditions(
                air_temperature_c=25.0,
                track_temperature_c=33.0,
                grip_level=0.98,
            )
        ),
    )


def test_lap_event_creates_parent_session(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaPersistenceService(
            database_session
        )
    )

    event_value = build_lap_event()

    lap = service.save_lap_event(
        event_value
    )

    session_record = (
        database_session.get(
            SessionRecord,
            event_value.session_id,
        )
    )

    assert session_record is not None

    assert (
        session_record.session_type
        == "practice"
    )

    assert (
        session_record.source
        == "assetto_corsa"
    )

    assert lap.id is not None

    assert (
        lap.session_id
        == event_value.session_id
    )


def test_sector_event_creates_parent_session(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaPersistenceService(
            database_session
        )
    )

    event_value = build_sector_event()

    sector = (
        service.save_sector_event(
            event_value
        )
    )

    session_record = (
        database_session.get(
            SessionRecord,
            event_value.session_id,
        )
    )

    assert session_record is not None

    assert sector.id is not None

    assert (
        sector.session_id
        == event_value.session_id
    )


def test_lap_event_is_persisted(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaPersistenceService(
            database_session
        )
    )

    event_value = build_lap_event()

    saved = service.save_lap_event(
        event_value
    )

    stored = database_session.get(
        LapRecord,
        saved.id,
    )

    assert stored is not None

    assert stored.lap_number == 1

    assert (
        stored.lap_time_ms
        == 104532
    )

    assert stored.is_best


def test_sector_event_is_persisted(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaPersistenceService(
            database_session
        )
    )

    event_value = build_sector_event()

    saved = (
        service.save_sector_event(
            event_value
        )
    )

    stored = database_session.get(
        SectorRecord,
        saved.id,
    )

    assert stored is not None

    assert stored.lap_number == 1

    assert (
        stored.sector_number
        == 1
    )

    assert (
        stored.sector_time_ms
        == 33184
    )


def test_completed_metadata_updates_live_session(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaPersistenceService(
            database_session
        )
    )

    service.save_lap_event(
        build_lap_event()
    )

    before = database_session.get(
        SessionRecord,
        "ac-session-001",
    )

    assert before is not None
    assert before.ended_at is None

    metadata = build_metadata()

    service.save_completed_session(
        metadata
    )

    after = database_session.get(
        SessionRecord,
        "ac-session-001",
    )

    assert after is not None

    assert (
        after.ended_at
        == metadata.ended_at
    )

    assert after.conditions is not None

    assert (
        after.conditions[
            "sample_count"
        ]
        == 12000
    )

    assert (
        after.conditions[
            "duration_seconds"
        ]
        == 600.0
    )


def test_car_and_track_are_not_duplicated(
    database_session: Session,
) -> None:
    service = (
        AssettoCorsaPersistenceService(
            database_session
        )
    )

    service.save_lap_event(
        build_lap_event()
    )

    service.save_sector_event(
        build_sector_event()
    )

    car_count = len(
        service.car_repository.list_all()
    )

    track_count = len(
        service.track_repository.list_all()
    )

    assert car_count == 1
    assert track_count == 1