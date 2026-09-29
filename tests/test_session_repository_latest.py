from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import (
    CarRecord,
)
from ac_race_engineer.database.repositories.sessions import (
    SessionRepository,
)

NOW = datetime(
    2026,
    9,
    28,
    18,
    0,
    tzinfo=timezone.utc,
)


def test_get_latest_session() -> None:
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
        car = CarRecord(
            car_key="mx5",
            name="MX-5",
        )

        session.add(
            car
        )

        session.flush()

        repository = (
            SessionRepository(
                session
            )
        )

        first = repository.save(
            session_id="session-1",
            car_id=car.id,
            session_type="practice",
            source="assetto_corsa",
            started_at=NOW,
        )

        second = repository.save(
            session_id="session-2",
            car_id=car.id,
            session_type="practice",
            source="assetto_corsa",
            started_at=(
                NOW
                + timedelta(
                    minutes=10
                )
            ),
        )

        first.created_at = NOW

        second.created_at = (
            NOW
            + timedelta(
                minutes=10
            )
        )

        session.flush()

        latest = (
            repository.get_latest()
        )

        assert latest is not None

        assert (
            latest.id
            == "session-2"
        )

    finally:
        session.close()
        engine.dispose()


def test_get_latest_filters_source() -> None:
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
        car = CarRecord(
            car_key="mx5",
            name="MX-5",
        )

        session.add(
            car
        )

        session.flush()

        repository = (
            SessionRepository(
                session
            )
        )

        ac_session = repository.save(
            session_id="ac-session",
            car_id=car.id,
            session_type="practice",
            source="assetto_corsa",
            started_at=NOW,
        )

        other_session = (
            repository.save(
                session_id="sim-session",
                car_id=car.id,
                session_type="test",
                source="simulator",
                started_at=(
                    NOW
                    + timedelta(
                        minutes=20
                    )
                ),
            )
        )

        ac_session.created_at = NOW

        other_session.created_at = (
            NOW
            + timedelta(
                minutes=20
            )
        )

        session.flush()

        latest = (
            repository.get_latest(
                source="assetto_corsa"
            )
        )

        assert latest is not None

        assert (
            latest.id
            == "ac-session"
        )

    finally:
        session.close()
        engine.dispose()