from dataclasses import replace

import pytest

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.session_tracker import (
    ACSessionType,
    ACStatus,
    AssettoCorsaSessionTracker,
    map_ac_session_type,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            ACSessionType.PRACTICE,
            SessionType.PRACTICE,
        ),
        (
            ACSessionType.QUALIFY,
            SessionType.QUALIFYING,
        ),
        (
            ACSessionType.RACE,
            SessionType.RACE,
        ),
        (
            ACSessionType.HOTLAP,
            SessionType.HOTLAP,
        ),
        (
            ACSessionType.TIME_ATTACK,
            SessionType.HOTLAP,
        ),
        (
            ACSessionType.DRIFT,
            SessionType.TEST,
        ),
        (
            ACSessionType.DRAG,
            SessionType.TEST,
        ),
        (
            ACSessionType.UNKNOWN,
            SessionType.TEST,
        ),
        (
            999,
            SessionType.TEST,
        ),
    ],
)
def test_maps_session_type(
    raw: int,
    expected: SessionType,
) -> None:
    assert (
        map_ac_session_type(raw)
        == expected
    )


def test_first_frame_starts_session() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    graphics = backend.read_graphics()
    static = backend.read_static()

    update = tracker.update(
        graphics,
        static,
    )

    assert update.new_session

    assert (
        update.ac_status
        == ACStatus.LIVE
    )

    assert (
        update.session_type
        == SessionType.PRACTICE
    )


def test_same_session_does_not_restart() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    static = backend.read_static()

    first = backend.read_graphics()

    tracker.update(
        first,
        static,
    )

    second = replace(
        first,
        packet_id=(
            first.packet_id + 1
        ),
        current_time_ms=80000,
    )

    update = tracker.update(
        second,
        static,
    )

    assert not update.new_session


def test_detects_completed_lap() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    static = backend.read_static()
    first = backend.read_graphics()

    tracker.update(
        first,
        static,
    )

    second = replace(
        first,
        packet_id=(
            first.packet_id + 1
        ),
        completed_laps=(
            first.completed_laps + 1
        ),
        last_time_ms=104700,
        current_time_ms=50,
    )

    update = tracker.update(
        second,
        static,
    )

    assert update.lap_completed

    assert (
        update.last_time_ms
        == 104700
    )


def test_detects_sector_change() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    static = backend.read_static()
    first = backend.read_graphics()

    tracker.update(
        first,
        static,
    )

    second = replace(
        first,
        packet_id=(
            first.packet_id + 1
        ),
        current_sector_index=2,
        last_sector_time_ms=33100,
    )

    update = tracker.update(
        second,
        static,
    )

    assert update.sector_changed

    assert (
        update.current_sector_index
        == 2
    )


def test_session_type_change_starts_new_session() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    static = backend.read_static()
    first = backend.read_graphics()

    tracker.update(
        first,
        static,
    )

    qualifying = replace(
        first,
        packet_id=(
            first.packet_id + 1
        ),
        session_type=(
            ACSessionType.QUALIFY
        ),
    )

    update = tracker.update(
        qualifying,
        static,
    )

    assert update.new_session

    assert (
        update.session_type
        == SessionType.QUALIFYING
    )


def test_track_change_starts_new_session() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    graphics = backend.read_graphics()
    static = backend.read_static()

    tracker.update(
        graphics,
        static,
    )

    new_track = replace(
        static,
        track="monza",
    )

    update = tracker.update(
        replace(
            graphics,
            packet_id=(
                graphics.packet_id + 1
            ),
        ),
        new_track,
    )

    assert update.new_session


def test_car_change_starts_new_session() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    graphics = backend.read_graphics()
    static = backend.read_static()

    tracker.update(
        graphics,
        static,
    )

    new_car = replace(
        static,
        car_model="ks_porsche_911_gt3_cup",
    )

    update = tracker.update(
        replace(
            graphics,
            packet_id=(
                graphics.packet_id + 1
            ),
        ),
        new_car,
    )

    assert update.new_session


def test_lap_counter_reset_starts_new_session() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    static = backend.read_static()
    graphics = backend.read_graphics()

    tracker.update(
        graphics,
        static,
    )

    reset = replace(
        graphics,
        packet_id=(
            graphics.packet_id + 1
        ),
        completed_laps=0,
    )

    update = tracker.update(
        reset,
        static,
    )

    assert update.new_session


def test_pause_resume_does_not_restart_session() -> None:
    backend = FakeAssettoCorsaBackend()

    tracker = (
        AssettoCorsaSessionTracker()
    )

    static = backend.read_static()

    live = backend.read_graphics()

    tracker.update(
        live,
        static,
    )

    paused = replace(
        live,
        packet_id=(
            live.packet_id + 1
        ),
        status=ACStatus.PAUSE,
    )

    paused_update = tracker.update(
        paused,
        static,
    )

    assert not paused_update.new_session

    resumed = replace(
        paused,
        packet_id=(
            paused.packet_id + 1
        ),
        status=ACStatus.LIVE,
    )

    resumed_update = tracker.update(
        resumed,
        static,
    )

    assert not resumed_update.new_session