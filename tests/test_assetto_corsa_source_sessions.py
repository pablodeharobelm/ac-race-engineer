from dataclasses import replace

from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.session_tracker import (
    ACSessionType,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


class MutableAssettoCorsaBackend(
    FakeAssettoCorsaBackend
):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.graphics_override = None
        self.static_override = None

    def read_graphics(
        self,
    ):
        original = super().read_graphics()

        if self.graphics_override is None:
            return original

        return replace(
            self.graphics_override,
            packet_id=self.packet_id,
        )

    def read_static(
        self,
    ):
        if self.static_override is not None:
            return self.static_override

        return super().read_static()


def test_first_frame_starts_real_source_session() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    frame = source.read_frame()

    assert frame.sample_index == 1

    assert (
        source.last_session_update
        is not None
    )

    assert (
        source.last_session_update.new_session
    )


def test_same_ac_session_keeps_session_id() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    first = source.read_frame()
    second = source.read_frame()

    assert (
        first.session_id
        == second.session_id
    )

    assert first.sample_index == 1
    assert second.sample_index == 2


def test_session_type_change_creates_new_session() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    first = source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        session_type=(
            ACSessionType.QUALIFY
        ),
    )

    second = source.read_frame()

    assert (
        first.session_id
        != second.session_id
    )

    assert second.sample_index == 1

    assert (
        source.last_session_update
        is not None
    )

    assert (
        source.last_session_update.new_session
    )


def test_new_session_resets_elapsed_time() -> None:
    class FakeClock:
        def __init__(
            self,
        ) -> None:
            self.value = 100.0

        def __call__(
            self,
        ) -> float:
            return self.value

        def advance(
            self,
            seconds: float,
        ) -> None:
            self.value += seconds

    clock = FakeClock()

    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend,
        clock=clock,
    )

    first = source.read_frame()

    clock.advance(
        30.0
    )

    second = source.read_frame()

    assert (
        second.elapsed_seconds
        > first.elapsed_seconds
    )

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        session_type=(
            ACSessionType.RACE
        ),
    )

    clock.advance(
        10.0
    )

    third = source.read_frame()

    assert third.sample_index == 1

    assert (
        third.elapsed_seconds
        == 0.0
    )


def test_track_change_creates_new_session() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    first = source.read_frame()

    current_static = (
        backend.read_static()
    )

    backend.static_override = replace(
        current_static,
        track="monza",
    )

    second = source.read_frame()

    assert (
        first.session_id
        != second.session_id
    )

    assert second.track_id == "monza"

    assert second.sample_index == 1


def test_car_change_creates_new_session() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    first = source.read_frame()

    current_static = (
        backend.read_static()
    )

    backend.static_override = replace(
        current_static,
        car_model=(
            "ks_porsche_911_gt3_cup"
        ),
    )

    second = source.read_frame()

    assert (
        first.session_id
        != second.session_id
    )

    assert (
        second.car_id
        == "ks_porsche_911_gt3_cup"
    )

    assert second.sample_index == 1


def test_completed_lap_does_not_start_new_session() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    first = source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        completed_laps=(
            graphics.completed_laps + 1
        ),
        current_time_ms=100,
        last_time_ms=104500,
    )

    second = source.read_frame()

    assert (
        first.session_id
        == second.session_id
    )

    assert second.sample_index == 2

    assert (
        source.last_session_update
        is not None
    )

    assert (
        source.last_session_update.lap_completed
    )


def test_sector_change_does_not_start_new_session() -> None:
    backend = (
        MutableAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    first = source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        current_sector_index=(
            graphics.current_sector_index + 1
        ),
        last_sector_time_ms=33000,
    )

    second = source.read_frame()

    assert (
        first.session_id
        == second.session_id
    )

    assert (
        source.last_session_update
        is not None
    )

    assert (
        source.last_session_update.sector_changed
    )