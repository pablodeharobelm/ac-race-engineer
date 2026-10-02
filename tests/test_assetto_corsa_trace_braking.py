import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    AssettoCorsaBrakingZoneService,
)


def sample(
    *,
    progress: float,
    elapsed: float,
    speed: float,
    brake: float = 0.0,
    throttle: float = 1.0,
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


def build_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.00,
            elapsed=0.0,
            speed=150.0,
        ),
        sample(
            progress=0.10,
            elapsed=10.0,
            speed=160.0,
        ),
        sample(
            progress=0.20,
            elapsed=20.0,
            speed=155.0,
            brake=0.20,
        ),
        sample(
            progress=0.22,
            elapsed=21.0,
            speed=140.0,
            brake=0.70,
        ),
        sample(
            progress=0.24,
            elapsed=22.0,
            speed=120.0,
            brake=1.00,
        ),
        sample(
            progress=0.26,
            elapsed=23.0,
            speed=100.0,
            brake=0.50,
        ),
        sample(
            progress=0.28,
            elapsed=24.0,
            speed=95.0,
        ),
        sample(
            progress=0.50,
            elapsed=50.0,
            speed=170.0,
        ),
        sample(
            progress=0.60,
            elapsed=60.0,
            speed=165.0,
            brake=0.30,
        ),
        sample(
            progress=0.62,
            elapsed=61.0,
            speed=145.0,
            brake=0.80,
        ),
        sample(
            progress=0.64,
            elapsed=62.0,
            speed=130.0,
            brake=0.40,
        ),
        sample(
            progress=0.66,
            elapsed=63.0,
            speed=125.0,
        ),
        sample(
            progress=1.00,
            elapsed=100.0,
            speed=155.0,
        ),
    )


def test_detects_two_braking_zones() -> None:
    service = (
        AssettoCorsaBrakingZoneService()
    )

    zones = service.analyze(
        build_trace()
    )

    assert len(
        zones
    ) == 2

    assert (
        zones[0].zone_number
        == 1
    )

    assert (
        zones[1].zone_number
        == 2
    )


def test_first_braking_zone_progress() -> None:
    service = (
        AssettoCorsaBrakingZoneService()
    )

    zones = service.analyze(
        build_trace()
    )

    first = zones[0]

    assert (
        first.start_progress
        == pytest.approx(
            0.20
        )
    )

    assert (
        first.end_progress
        == pytest.approx(
            0.26
        )
    )

    assert (
        first.center_progress
        == pytest.approx(
            0.23
        )
    )

    assert (
        first.progress_span
        == pytest.approx(
            0.06
        )
    )


def test_first_braking_zone_timing() -> None:
    service = (
        AssettoCorsaBrakingZoneService()
    )

    first = service.analyze(
        build_trace()
    )[0]

    assert (
        first.start_elapsed_seconds
        == pytest.approx(
            20.0
        )
    )

    assert (
        first.end_elapsed_seconds
        == pytest.approx(
            23.0
        )
    )

    assert (
        first.duration_seconds
        == pytest.approx(
            3.0
        )
    )


def test_first_braking_zone_speed_metrics() -> None:
    service = (
        AssettoCorsaBrakingZoneService()
    )

    first = service.analyze(
        build_trace()
    )[0]

    assert (
        first.entry_speed_kmh
        == pytest.approx(
            155.0
        )
    )

    assert (
        first.minimum_speed_kmh
        == pytest.approx(
            100.0
        )
    )

    assert (
        first.exit_speed_kmh
        == pytest.approx(
            100.0
        )
    )


def test_first_braking_zone_brake_metrics() -> None:
    service = (
        AssettoCorsaBrakingZoneService()
    )

    first = service.analyze(
        build_trace()
    )[0]

    assert (
        first.peak_brake
        == pytest.approx(
            1.0
        )
    )

    assert (
        first.average_brake
        == pytest.approx(
            0.6
        )
    )

    assert (
        first.sample_count
        == 4
    )


def test_custom_threshold_changes_detection() -> None:
    service = (
        AssettoCorsaBrakingZoneService(
            brake_threshold=0.60,
            minimum_samples=2,
        )
    )

    zones = service.analyze(
        build_trace()
    )

    assert len(
        zones
    ) == 1

    first = zones[0]

    assert (
        first.start_progress
        == pytest.approx(
            0.22
        )
    )

    assert (
        first.end_progress
        == pytest.approx(
            0.24
        )
    )


def test_ignores_short_brake_tap() -> None:
    trace = (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=0.5,
            elapsed=50.0,
            speed=100.0,
            brake=0.5,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
            speed=100.0,
        ),
    )

    service = (
        AssettoCorsaBrakingZoneService(
            minimum_samples=2
        )
    )

    zones = service.analyze(
        trace
    )

    assert zones == ()


def test_single_sample_zone_can_be_enabled() -> None:
    trace = (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=0.5,
            elapsed=50.0,
            speed=90.0,
            brake=0.8,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
            speed=100.0,
        ),
    )

    service = (
        AssettoCorsaBrakingZoneService(
            minimum_samples=1
        )
    )

    zones = service.analyze(
        trace
    )

    assert len(
        zones
    ) == 1

    assert (
        zones[0].duration_seconds
        == pytest.approx(
            0.0
        )
    )


def test_no_braking_returns_empty_tuple() -> None:
    trace = (
        sample(
            progress=0.0,
            elapsed=0.0,
            speed=100.0,
        ),
        sample(
            progress=0.5,
            elapsed=50.0,
            speed=120.0,
        ),
        sample(
            progress=1.0,
            elapsed=100.0,
            speed=130.0,
        ),
    )

    service = (
        AssettoCorsaBrakingZoneService()
    )

    assert (
        service.analyze(
            trace
        )
        == ()
    )


def test_empty_trace_returns_empty_tuple() -> None:
    service = (
        AssettoCorsaBrakingZoneService()
    )

    assert (
        service.analyze(
            ()
        )
        == ()
    )


def test_rejects_invalid_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="brake_threshold",
    ):
        AssettoCorsaBrakingZoneService(
            brake_threshold=0.0
        )

    with pytest.raises(
        ValueError,
        match="brake_threshold",
    ):
        AssettoCorsaBrakingZoneService(
            brake_threshold=1.1
        )


def test_rejects_invalid_minimum_samples() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_samples",
    ):
        AssettoCorsaBrakingZoneService(
            minimum_samples=0
        )


def test_rejects_decreasing_progress() -> None:
    trace = (
        sample(
            progress=0.5,
            elapsed=10.0,
            speed=100.0,
        ),
        sample(
            progress=0.4,
            elapsed=11.0,
            speed=100.0,
        ),
    )

    service = (
        AssettoCorsaBrakingZoneService()
    )

    with pytest.raises(
        ValueError,
        match="progress",
    ):
        service.analyze(
            trace
        )


def test_rejects_decreasing_elapsed_time() -> None:
    trace = (
        sample(
            progress=0.4,
            elapsed=11.0,
            speed=100.0,
        ),
        sample(
            progress=0.5,
            elapsed=10.0,
            speed=100.0,
        ),
    )

    service = (
        AssettoCorsaBrakingZoneService()
    )

    with pytest.raises(
        ValueError,
        match="elapsed time",
    ):
        service.analyze(
            trace
        )