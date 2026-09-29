
import pytest

from ac_race_engineer.telemetry.assetto_corsa.exceptions import (
    AssettoCorsaStaleDataError,
)
from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


def test_source_name() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    assert source.source_name == "assetto_corsa"


def test_source_returns_frame() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    frame = source.read_frame()

    assert frame.car_id == (
        "ks_mazda_mx5_cup"
    )

    assert frame.track_id == "magione"

    assert frame.vehicle.speed_kmh == 143.2
    assert frame.vehicle.rpm == 6150
    assert frame.vehicle.gear == 3


def test_source_keeps_same_session() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    first = source.read_frame()
    second = source.read_frame()

    assert (
        first.session_id
        == second.session_id
    )


def test_source_increments_sample_index() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    first = source.read_frame()
    second = source.read_frame()
    third = source.read_frame()

    assert first.sample_index == 1
    assert second.sample_index == 2
    assert third.sample_index == 3


def test_elapsed_time_increases() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    first = source.read_frame()
    second = source.read_frame()

    assert (
        second.elapsed_seconds
        >= first.elapsed_seconds
    )


def test_timestamp_is_timezone_aware() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    frame = source.read_frame()

    assert frame.timestamp.tzinfo is not None

    assert (
        frame.timestamp.utcoffset()
        is not None
    )


def test_source_returns_all_four_wheels() -> None:
    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend()
    )

    frame = source.read_frame()

    assert set(frame.wheels) == {
        "FL",
        "FR",
        "RL",
        "RR",
    }

class FakeClock:
    def __init__(
        self,
        initial: float = 100.0,
    ) -> None:
        self.value = initial

    def __call__(
        self,
    ) -> float:
        return self.value

    def advance(
        self,
        seconds: float,
    ) -> None:
        self.value += seconds


class StaleAssettoCorsaBackend(
    FakeAssettoCorsaBackend
):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self._physics = (
            super().read_physics()
        )

    def read_physics(
        self,
    ):
        return self._physics


def test_rejects_invalid_stale_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="stale_timeout_seconds",
    ):
        AssettoCorsaSource(
            FakeAssettoCorsaBackend(),
            stale_timeout_seconds=0.0,
        )


def test_same_packet_is_allowed_before_timeout() -> None:
    clock = FakeClock()

    source = AssettoCorsaSource(
        StaleAssettoCorsaBackend(),
        stale_timeout_seconds=2.0,
        clock=clock,
    )

    first = source.read_frame()

    clock.advance(
        1.5
    )

    second = source.read_frame()

    assert first.sample_index == 1
    assert second.sample_index == 2


def test_same_packet_becomes_stale() -> None:
    clock = FakeClock()

    source = AssettoCorsaSource(
        StaleAssettoCorsaBackend(),
        stale_timeout_seconds=2.0,
        clock=clock,
    )

    source.read_frame()

    clock.advance(
        2.1
    )

    with pytest.raises(
        AssettoCorsaStaleDataError,
        match="stopped updating",
    ):
        source.read_frame()


def test_stale_detection_can_be_disabled() -> None:
    clock = FakeClock()

    source = AssettoCorsaSource(
        StaleAssettoCorsaBackend(),
        stale_timeout_seconds=None,
        clock=clock,
    )

    source.read_frame()

    clock.advance(
        500.0
    )

    frame = source.read_frame()

    assert frame.sample_index == 2


def test_new_packets_reset_stale_timer() -> None:
    clock = FakeClock()

    source = AssettoCorsaSource(
        FakeAssettoCorsaBackend(),
        stale_timeout_seconds=1.0,
        clock=clock,
    )

    first = source.read_frame()

    clock.advance(
        10.0
    )

    second = source.read_frame()

    assert (
        second.sample_index
        == first.sample_index + 1
    )