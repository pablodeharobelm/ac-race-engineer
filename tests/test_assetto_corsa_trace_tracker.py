from dataclasses import replace

import pytest

from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_tracker import (
    AssettoCorsaLapTraceTracker,
)


def build_frame_and_graphics():
    backend = FakeAssettoCorsaBackend()

    source = AssettoCorsaSource(
        backend,
        stale_timeout_seconds=None,
    )

    frame = source.read_frame()
    graphics = backend.read_graphics()

    return frame, graphics


def test_builds_complete_lap_trace() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    first = replace(
        graphics,
        completed_laps=0,
        normalized_car_position=0.01,
        current_time_ms=500,
    )

    middle = replace(
        graphics,
        completed_laps=0,
        normalized_car_position=0.50,
        current_time_ms=50000,
    )

    end = replace(
        graphics,
        completed_laps=0,
        normalized_car_position=0.98,
        current_time_ms=99000,
    )

    next_lap = replace(
        graphics,
        completed_laps=1,
        normalized_car_position=0.01,
        current_time_ms=500,
        last_time_ms=100000,
    )

    assert (
        tracker.update(
            frame=frame,
            graphics=first,
        )
        is None
    )

    assert (
        tracker.update(
            frame=frame,
            graphics=middle,
        )
        is None
    )

    assert (
        tracker.update(
            frame=frame,
            graphics=end,
        )
        is None
    )

    trace = tracker.update(
        frame=frame,
        graphics=next_lap,
    )

    assert trace is not None
    assert trace.lap_number == 1
    assert trace.lap_time_ms == 100000
    assert trace.sample_count == 3

    assert (
        trace.samples[0].progress
        == pytest.approx(
            0.01
        )
    )

    assert (
        trace.samples[-1].progress
        == pytest.approx(
            0.98
        )
    )


def test_trace_contains_driving_inputs() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.01,
            current_time_ms=500,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.98,
            current_time_ms=99000,
        ),
    )

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=1,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert trace is not None

    middle = trace.samples[1]

    assert (
        middle.speed_kmh
        == frame.vehicle.speed_kmh
    )

    assert (
        middle.throttle
        == frame.vehicle.throttle
    )

    assert (
        middle.brake
        == frame.vehicle.brake
    )

    assert (
        middle.steering_angle_deg
        == frame.vehicle.steering_angle_deg
    )


def test_discards_initial_partial_lap() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=2,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=2,
            normalized_car_position=0.98,
            current_time_ms=99000,
        ),
    )

    partial = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=3,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert partial is None

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=3,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=3,
            normalized_car_position=0.98,
            current_time_ms=99000,
        ),
    )

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=4,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert trace is not None
    assert trace.lap_number == 4


def test_reset_discards_partial_trace() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.01,
            current_time_ms=500,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.reset()

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=1,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert trace is None


def test_rejects_trace_without_enough_samples() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker(
            minimum_samples=3
        )
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.01,
            current_time_ms=500,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.98,
            current_time_ms=99000,
        ),
    )

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=1,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert trace is None


def test_rejects_trace_that_does_not_reach_end_threshold() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.01,
            current_time_ms=500,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.80,
            current_time_ms=80000,
        ),
    )

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=1,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert trace is None


def test_rejects_non_positive_lap_time() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.01,
            current_time_ms=500,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.98,
            current_time_ms=99000,
        ),
    )

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=1,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=0,
        ),
    )

    assert trace is None


def test_duplicate_progress_replaces_previous_sample() -> None:
    (
        frame,
        graphics,
    ) = build_frame_and_graphics()

    tracker = (
        AssettoCorsaLapTraceTracker()
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.01,
            current_time_ms=500,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.50,
            current_time_ms=49000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.50,
            current_time_ms=50000,
        ),
    )

    tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=0,
            normalized_car_position=0.98,
            current_time_ms=99000,
        ),
    )

    trace = tracker.update(
        frame=frame,
        graphics=replace(
            graphics,
            completed_laps=1,
            normalized_car_position=0.01,
            current_time_ms=500,
            last_time_ms=100000,
        ),
    )

    assert trace is not None
    assert trace.sample_count == 3

    assert (
        trace.samples[1].elapsed_seconds
        == pytest.approx(
            50.0
        )
    )


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="start_progress_threshold",
    ):
        AssettoCorsaLapTraceTracker(
            start_progress_threshold=-0.1
        )

    with pytest.raises(
        ValueError,
        match="end_progress_threshold",
    ):
        AssettoCorsaLapTraceTracker(
            end_progress_threshold=0.0
        )

    with pytest.raises(
        ValueError,
        match=(
            "greater than "
            "start_progress_threshold"
        ),
    ):
        AssettoCorsaLapTraceTracker(
            start_progress_threshold=0.5,
            end_progress_threshold=0.4,
        )

    with pytest.raises(
        ValueError,
        match="minimum_samples",
    ):
        AssettoCorsaLapTraceTracker(
            minimum_samples=1
        )