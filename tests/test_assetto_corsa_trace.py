import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AssettoCorsaTraceComparisonService,
    DrivingTraceSample,
)


def sample(
    *,
    progress: float,
    elapsed: float,
    speed: float,
    throttle: float = 1.0,
    brake: float = 0.0,
    steering: float = 0.0,
) -> DrivingTraceSample:
    return DrivingTraceSample(
        progress=progress,
        elapsed_seconds=elapsed,
        speed_kmh=speed,
        throttle=throttle,
        brake=brake,
        steering_angle_deg=steering,
    )


def reference_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=0.5,
            elapsed=50.0,
            speed=80.0,
            throttle=0.0,
            brake=1.0,
            steering=15.0,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
            speed=120.0,
        ),
    )


def target_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=0.25,
            elapsed=25.5,
            speed=91.0,
        ),
        sample(
            progress=0.5,
            elapsed=51.0,
            speed=74.0,
            throttle=0.0,
            brake=1.0,
            steering=17.0,
        ),
        sample(
            progress=0.75,
            elapsed=76.5,
            speed=101.0,
        ),
        sample(
            progress=1.0,
            elapsed=102.0,
            speed=120.0,
        ),
    )


def test_aligns_traces_to_common_grid() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
        grid_points=5,
    )

    assert len(
        result.points
    ) == 5

    assert [
        point.progress
        for point in result.points
    ] == pytest.approx(
        [
            0.0,
            0.25,
            0.5,
            0.75,
            1.0,
        ]
    )


def test_interpolates_reference_trace() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
        grid_points=5,
    )

    quarter = result.points[
        1
    ]

    assert (
        quarter.reference_speed_kmh
        == pytest.approx(
            90.0
        )
    )

    assert (
        quarter.reference_elapsed_seconds
        == pytest.approx(
            25.0
        )
    )


def test_calculates_time_delta() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
        grid_points=5,
    )

    halfway = result.points[
        2
    ]

    assert (
        halfway.time_delta_seconds
        == pytest.approx(
            1.0
        )
    )

    assert (
        result.final_time_delta_seconds
        == pytest.approx(
            2.0
        )
    )


def test_calculates_speed_delta() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
        grid_points=5,
    )

    halfway = result.points[
        2
    ]

    assert (
        halfway.speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )


def test_calculates_control_deltas() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    target = (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=0.5,
            elapsed=51.0,
            speed=80.0,
            throttle=0.2,
            brake=0.8,
            steering=20.0,
        ),
        sample(
            progress=1.0,
            elapsed=102.0,
            speed=120.0,
        ),
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target,
        grid_points=3,
    )

    halfway = result.points[
        1
    ]

    assert (
        halfway.throttle_delta
        == pytest.approx(
            0.2
        )
    )

    assert (
        halfway.brake_delta
        == pytest.approx(
            -0.2
        )
    )

    assert (
        halfway.steering_delta_deg
        == pytest.approx(
            5.0
        )
    )


def test_detects_largest_speed_loss() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference_trace(),
        target_trace=target_trace(),
        grid_points=5,
    )

    assert (
        result.largest_speed_loss_progress
        == pytest.approx(
            0.5
        )
    )


def test_supports_partial_overlap() -> None:
    reference = (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
            speed=120.0,
        ),
    )

    target = (
        sample(
            progress=0.2,
            elapsed=20.0,
            speed=100.0,
        ),
        sample(
            progress=0.8,
            elapsed=80.0,
            speed=120.0,
        ),
    )

    service = (
        AssettoCorsaTraceComparisonService()
    )

    result = service.compare(
        reference_lap_number=1,
        target_lap_number=2,
        reference_trace=reference,
        target_trace=target,
        grid_points=3,
    )

    assert (
        result.start_progress
        == pytest.approx(
            0.2
        )
    )

    assert (
        result.end_progress
        == pytest.approx(
            0.8
        )
    )


def test_rejects_single_sample_trace() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    with pytest.raises(
        ValueError,
        match="at least two samples",
    ):
        service.compare(
            reference_lap_number=1,
            target_lap_number=2,
            reference_trace=(
                sample(
                    progress=0.0,
                    elapsed=0.0,
                    speed=100.0,
                ),
            ),
            target_trace=target_trace(),
        )


def test_rejects_invalid_progress() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    invalid = (
        sample(
            progress=-0.1,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
            speed=120.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="progress",
    ):
        service.compare(
            reference_lap_number=1,
            target_lap_number=2,
            reference_trace=invalid,
            target_trace=target_trace(),
        )


def test_rejects_same_lap() -> None:
    service = (
        AssettoCorsaTraceComparisonService()
    )

    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        service.compare(
            reference_lap_number=1,
            target_lap_number=1,
            reference_trace=reference_trace(),
            target_trace=target_trace(),
        )