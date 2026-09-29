from dataclasses import replace
from datetime import datetime, timezone

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.lap_sector_tracker import (
    AssettoCorsaLapSectorTracker,
)

TIMESTAMP = datetime.now(
    timezone.utc
)


def update_tracker(
    tracker: AssettoCorsaLapSectorTracker,
    graphics,
):
    return tracker.update(
        graphics=graphics,
        timestamp=TIMESTAMP,
        session_id="session-1",
        car_id="ks_mazda_mx5_cup",
        track_id="magione",
        session_type=(
            SessionType.PRACTICE
        ),
    )


def test_first_snapshot_produces_no_events() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaLapSectorTracker()
    )

    graphics = (
        backend.read_graphics()
    )

    lap_event, sector_event = (
        update_tracker(
            tracker,
            graphics,
        )
    )

    assert lap_event is None
    assert sector_event is None


def test_detects_completed_lap() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaLapSectorTracker()
    )

    first = (
        backend.read_graphics()
    )

    update_tracker(
        tracker,
        first,
    )

    second = replace(
        first,
        packet_id=(
            first.packet_id + 1
        ),
        completed_laps=(
            first.completed_laps + 1
        ),
        last_time_ms=104500,
        best_time_ms=104500,
    )

    lap_event, _ = update_tracker(
        tracker,
        second,
    )

    assert lap_event is not None

    assert (
        lap_event.lap_number
        == 3
    )

    assert (
        lap_event.lap_time_ms
        == 104500
    )

    assert (
        lap_event.best_lap_time_ms
        == 104500
    )

    assert lap_event.is_best


def test_non_best_lap() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaLapSectorTracker()
    )

    first = (
        backend.read_graphics()
    )

    update_tracker(
        tracker,
        first,
    )

    second = replace(
        first,
        completed_laps=(
            first.completed_laps + 1
        ),
        last_time_ms=106000,
        best_time_ms=104500,
    )

    lap_event, _ = update_tracker(
        tracker,
        second,
    )

    assert lap_event is not None

    assert not lap_event.is_best


def test_detects_completed_sector() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaLapSectorTracker()
    )

    first = (
        backend.read_graphics()
    )

    update_tracker(
        tracker,
        first,
    )

    second = replace(
        first,
        current_sector_index=(
            first.current_sector_index + 1
        ),
        last_sector_time_ms=33184,
    )

    _, sector_event = update_tracker(
        tracker,
        second,
    )

    assert sector_event is not None

    assert (
        sector_event.sector_index
        == first.current_sector_index
    )

    assert (
        sector_event.sector_number
        == first.current_sector_index + 1
    )

    assert (
        sector_event.sector_time_ms
        == 33184
    )


def test_same_snapshot_creates_no_duplicate_events() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaLapSectorTracker()
    )

    graphics = (
        backend.read_graphics()
    )

    update_tracker(
        tracker,
        graphics,
    )

    lap_event, sector_event = (
        update_tracker(
            tracker,
            graphics,
        )
    )

    assert lap_event is None
    assert sector_event is None


def test_reset_discards_previous_state() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaLapSectorTracker()
    )

    first = (
        backend.read_graphics()
    )

    update_tracker(
        tracker,
        first,
    )

    tracker.reset()

    changed = replace(
        first,
        completed_laps=(
            first.completed_laps + 1
        ),
        current_sector_index=(
            first.current_sector_index + 1
        ),
    )

    lap_event, sector_event = (
        update_tracker(
            tracker,
            changed,
        )
    )

    assert lap_event is None
    assert sector_event is None