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
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


class FakeClock:
    def __init__(
        self,
        value: float = 100.0,
    ) -> None:
        self.value = value

    def __call__(
        self,
    ) -> float:
        return self.value

    def advance(
        self,
        seconds: float,
    ) -> None:
        self.value += seconds


class MutableBackend(
    FakeAssettoCorsaBackend
):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.graphics_override = None

    def read_graphics(
        self,
    ):
        original = (
            super().read_graphics()
        )

        if self.graphics_override is None:
            return original

        return replace(
            self.graphics_override,
            packet_id=self.packet_id,
        )


def test_no_completed_session_initially() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    assert (
        source.last_completed_session
        is None
    )

    assert (
        source.completed_sessions_pending
        == 0
    )


def test_session_change_creates_metadata() -> None:
    clock = FakeClock()

    backend = MutableBackend()

    source = AssettoCorsaSource(
        backend,
        clock=clock,
    )

    first = source.read_frame()

    clock.advance(
        1.0
    )

    second = source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        session_type=(
            ACSessionType.QUALIFY
        ),
    )

    clock.advance(
        1.0
    )

    third = source.read_frame()

    metadata = (
        source.last_completed_session
    )

    assert metadata is not None

    assert (
        metadata.session_id
        == first.session_id
    )

    assert (
        metadata.session_id
        == second.session_id
    )

    assert (
        metadata.session_id
        != third.session_id
    )

    assert (
        metadata.car_id
        == "ks_mazda_mx5_cup"
    )

    assert (
        metadata.track_id
        == "magione"
    )

    assert (
        metadata.source
        == "assetto_corsa"
    )

    assert (
        metadata.session_type
        == SessionType.PRACTICE
    )

    assert (
        metadata.sample_count
        == 2
    )

    assert (
        metadata.duration_seconds
        == pytest.approx(1.0)
    )


def test_metadata_contains_conditions() -> None:
    clock = FakeClock()

    backend = MutableBackend()

    source = AssettoCorsaSource(
        backend,
        clock=clock,
    )

    source.read_frame()

    clock.advance(
        1.0
    )

    source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        session_type=(
            ACSessionType.RACE
        ),
    )

    source.read_frame()

    metadata = (
        source.last_completed_session
    )

    assert metadata is not None

    assert (
        metadata.initial_conditions.air_temperature_c
        == pytest.approx(24.0)
    )

    assert (
        metadata.initial_conditions.track_temperature_c
        == pytest.approx(31.0)
    )

    assert (
        metadata.initial_conditions.grip_level
        == pytest.approx(0.98)
    )

    assert (
        metadata.final_conditions.air_temperature_c
        == pytest.approx(24.0)
    )

    assert (
        metadata.final_conditions.track_temperature_c
        == pytest.approx(31.0)
    )


def test_completed_session_can_be_popped() -> None:
    backend = MutableBackend()

    source = AssettoCorsaSource(
        backend
    )

    source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        session_type=(
            ACSessionType.QUALIFY
        ),
    )

    source.read_frame()

    assert (
        source.completed_sessions_pending
        == 1
    )

    metadata = (
        source.pop_completed_session()
    )

    assert metadata is not None

    assert (
        metadata.session_type
        == SessionType.PRACTICE
    )

    assert (
        source.completed_sessions_pending
        == 0
    )

    assert (
        source.pop_completed_session()
        is None
    )


def test_finish_current_session() -> None:
    clock = FakeClock()

    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend(),
        clock=clock,
    )

    first = source.read_frame()

    clock.advance(
        5.0
    )

    second = source.read_frame()

    metadata = (
        source.finish_current_session()
    )

    assert metadata is not None

    assert (
        metadata.session_id
        == first.session_id
    )

    assert (
        metadata.session_id
        == second.session_id
    )

    assert (
        metadata.sample_count
        == 2
    )

    assert (
        metadata.duration_seconds
        == pytest.approx(5.0)
    )


def test_finish_current_session_only_once() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    source.read_frame()

    first_result = (
        source.finish_current_session()
    )

    second_result = (
        source.finish_current_session()
    )

    assert first_result is not None
    assert second_result is None


def test_read_after_manual_finish_starts_new_session() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    first = source.read_frame()

    source.finish_current_session()

    second = source.read_frame()

    assert (
        first.session_id
        != second.session_id
    )

    assert second.sample_index == 1


def test_metadata_ends_on_last_old_frame() -> None:
    clock = FakeClock()

    backend = MutableBackend()

    source = AssettoCorsaSource(
        backend,
        clock=clock,
    )

    source.read_frame()

    clock.advance(
        1.0
    )

    old_last_frame = (
        source.read_frame()
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
        1.0
    )

    new_frame = (
        source.read_frame()
    )

    metadata = (
        source.last_completed_session
    )

    assert metadata is not None

    assert (
        metadata.ended_at
        == old_last_frame.timestamp
    )

    assert (
        metadata.ended_at
        <= new_frame.timestamp
    )