from dataclasses import replace

from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


class TraceBackend(
    FakeAssettoCorsaBackend
):
    """
    Fake backend that simulates one complete lap.

    Samples:

        0.01
        0.50
        0.98
        finish line
        0.01

    The fourth read reports completed_laps=1,
    which closes lap 1 and starts lap 2.
    """

    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.graphics_index = 0

        self.graphics_values = (
            (
                0,
                0.01,
                500,
            ),
            (
                0,
                0.50,
                50000,
            ),
            (
                0,
                0.98,
                99000,
            ),
            (
                1,
                0.01,
                500,
            ),
        )

    def read_graphics(
        self,
    ):
        original = (
            super().read_graphics()
        )

        index = min(
            self.graphics_index,
            len(
                self.graphics_values
            )
            - 1,
        )

        (
            completed_laps,
            progress,
            current_time_ms,
        ) = self.graphics_values[
            index
        ]

        self.graphics_index += 1

        return replace(
            original,
            completed_laps=completed_laps,
            normalized_car_position=progress,
            current_time_ms=current_time_ms,
            last_time_ms=100000,
        )


def test_source_queues_completed_lap_trace() -> None:
    source = AssettoCorsaSource(
        TraceBackend(),
        stale_timeout_seconds=None,
    )

    for _ in range(
        4
    ):
        source.read_frame()

    assert (
        source.lap_traces_pending
        == 1
    )

    trace = (
        source.pop_lap_trace()
    )

    assert trace is not None

    assert (
        trace.lap_number
        == 1
    )

    assert (
        trace.lap_time_ms
        == 100000
    )

    assert (
        trace.sample_count
        == 3
    )

    assert (
        trace.car_id
        == "ks_mazda_mx5_cup"
    )

    assert (
        trace.track_id
        == "magione"
    )

    assert (
        source.lap_traces_pending
        == 0
    )


def test_source_exposes_last_lap_trace() -> None:
    source = AssettoCorsaSource(
        TraceBackend(),
        stale_timeout_seconds=None,
    )

    for _ in range(
        4
    ):
        source.read_frame()

    trace = (
        source.last_lap_trace
    )

    assert trace is not None

    assert (
        trace.lap_number
        == 1
    )

    assert (
        trace.sample_count
        == 3
    )


def test_pop_lap_trace_returns_none_when_empty() -> None:
    source = AssettoCorsaSource(
        TraceBackend(),
        stale_timeout_seconds=None,
    )

    assert (
        source.pop_lap_trace()
        is None
    )


def test_trace_samples_contain_expected_progress() -> None:
    source = AssettoCorsaSource(
        TraceBackend(),
        stale_timeout_seconds=None,
    )

    for _ in range(
        4
    ):
        source.read_frame()

    trace = (
        source.pop_lap_trace()
    )

    assert trace is not None

    progress = tuple(
        sample.progress
        for sample in trace.samples
    )

    assert progress == (
        0.01,
        0.50,
        0.98,
    )


def test_trace_samples_contain_vehicle_inputs() -> None:
    source = AssettoCorsaSource(
        TraceBackend(),
        stale_timeout_seconds=None,
    )

    frames = [
        source.read_frame()
        for _ in range(
            4
        )
    ]

    trace = (
        source.pop_lap_trace()
    )

    assert trace is not None

    first_sample = (
        trace.samples[0]
    )

    first_frame = (
        frames[0]
    )

    assert (
        first_sample.speed_kmh
        == first_frame.vehicle.speed_kmh
    )

    assert (
        first_sample.throttle
        == first_frame.vehicle.throttle
    )

    assert (
        first_sample.brake
        == first_frame.vehicle.brake
    )

    assert (
        first_sample.steering_angle_deg
        == first_frame.vehicle.steering_angle_deg
    )


def test_finish_session_discards_partial_trace() -> None:
    backend = TraceBackend()

    source = AssettoCorsaSource(
        backend,
        stale_timeout_seconds=None,
    )

    source.read_frame()
    source.read_frame()

    assert (
        source.lap_traces_pending
        == 0
    )

    metadata = (
        source.finish_current_session()
    )

    assert metadata is not None

    assert (
        source.lap_traces_pending
        == 0
    )

    assert (
        source.pop_lap_trace()
        is None
    )