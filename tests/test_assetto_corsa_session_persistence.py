from datetime import datetime, timezone
from unittest.mock import Mock

from ac_race_engineer.telemetry.assetto_corsa.session_persistence import (
    AssettoCorsaSessionPersistenceService,
)

from ac_race_engineer.domain.session import (
    SessionConditions,
    SessionMetadata,
    SessionType,
)


def build_metadata() -> SessionMetadata:
    return SessionMetadata(
        session_id="ac-session-001",
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        source="assetto_corsa",
        session_type=SessionType.PRACTICE,
        started_at=datetime(
            2026,
            9,
            28,
            18,
            0,
            tzinfo=timezone.utc,
        ),
        ended_at=datetime(
            2026,
            9,
            28,
            18,
            10,
            tzinfo=timezone.utc,
        ),
        sample_count=12000,
        duration_seconds=600.0,
        initial_conditions=SessionConditions(
            air_temperature_c=24.0,
            track_temperature_c=31.0,
            grip_level=0.97,
        ),
        final_conditions=SessionConditions(
            air_temperature_c=25.0,
            track_temperature_c=33.0,
            grip_level=0.98,
        ),
    )


def test_persists_existing_car_and_track(
    monkeypatch,
) -> None:
    database_session = Mock()

    service = (
        AssettoCorsaSessionPersistenceService(
            database_session
        )
    )

    car = Mock()
    car.id = 10

    track = Mock()
    track.id = 20

    service.car_repository.get_by_key = Mock(
        return_value=car
    )

    service.track_repository.get_by_key = Mock(
        return_value=track
    )

    saved_record = Mock()

    service.session_repository.save = Mock(
        return_value=saved_record
    )

    metadata = build_metadata()

    result = service.save_session(
        metadata
    )

    assert result is saved_record

    service.session_repository.save.assert_called_once()

    call = (
        service.session_repository.save.call_args
    )

    assert (
        call.kwargs["session_id"]
        == "ac-session-001"
    )

    assert (
        call.kwargs["car_id"]
        == 10
    )

    assert (
        call.kwargs["track_id"]
        == 20
    )

    assert (
        call.kwargs["source"]
        == "assetto_corsa"
    )


def test_creates_missing_car() -> None:
    database_session = Mock()

    service = (
        AssettoCorsaSessionPersistenceService(
            database_session
        )
    )

    service.car_repository.get_by_key = Mock(
        return_value=None
    )

    created_car = Mock()
    created_car.id = 1

    service.car_repository.save = Mock(
        return_value=created_car
    )

    track = Mock()
    track.id = 2

    service.track_repository.get_by_key = Mock(
        return_value=track
    )

    service.session_repository.save = Mock(
        return_value=Mock()
    )

    service.save_session(
        build_metadata()
    )

    service.car_repository.save.assert_called_once_with(
        car_key="ks_mazda_mx5_cup",
        name="ks_mazda_mx5_cup",
    )


def test_creates_missing_track() -> None:
    database_session = Mock()

    service = (
        AssettoCorsaSessionPersistenceService(
            database_session
        )
    )

    car = Mock()
    car.id = 1

    service.car_repository.get_by_key = Mock(
        return_value=car
    )

    service.track_repository.get_by_key = Mock(
        return_value=None
    )

    created_track = Mock()
    created_track.id = 2

    service.track_repository.save = Mock(
        return_value=created_track
    )

    service.session_repository.save = Mock(
        return_value=Mock()
    )

    service.save_session(
        build_metadata()
    )

    service.track_repository.save.assert_called_once_with(
        track_key="magione",
        name="magione",
    )


def test_persists_conditions() -> None:
    database_session = Mock()

    service = (
        AssettoCorsaSessionPersistenceService(
            database_session
        )
    )

    car = Mock()
    car.id = 1

    track = Mock()
    track.id = 2

    service.car_repository.get_by_key = Mock(
        return_value=car
    )

    service.track_repository.get_by_key = Mock(
        return_value=track
    )

    service.session_repository.save = Mock(
        return_value=Mock()
    )

    service.save_session(
        build_metadata()
    )

    call = (
        service.session_repository.save.call_args
    )

    conditions = (
        call.kwargs["conditions"]
    )

    assert (
        conditions["initial"]["air_temperature_c"]
        == 24.0
    )

    assert (
        conditions["initial"]["track_temperature_c"]
        == 31.0
    )

    assert (
        conditions["final"]["air_temperature_c"]
        == 25.0
    )

    assert (
        conditions["final"]["track_temperature_c"]
        == 33.0
    )