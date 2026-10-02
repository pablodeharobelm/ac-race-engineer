import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    BrakingZone,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    AssettoCorsaCornerEntryService,
)


def sample(
    *,
    progress: float,
    elapsed: float,
    speed: float,
    brake: float = 0.0,
    throttle: float = 0.0,
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


def braking_zone(
    *,
    zone_number: int,
    start: float,
    end: float,
    start_elapsed: float,
    end_elapsed: float,
) -> BrakingZone:
    return BrakingZone(
        zone_number=zone_number,
        start_progress=start,
        end_progress=end,
        start_elapsed_seconds=(
            start_elapsed
        ),
        end_elapsed_seconds=(
            end_elapsed
        ),
        duration_seconds=(
            end_elapsed
            - start_elapsed
        ),
        entry_speed_kmh=160.0,
        minimum_speed_kmh=120.0,
        exit_speed_kmh=120.0,
        peak_brake=0.90,
        average_brake=0.60,
        sample_count=4,
    )


def build_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.10,
            elapsed=10.0,
            speed=170.0,
            throttle=1.0,
        ),
        sample(
            progress=0.20,
            elapsed=20.0,
            speed=165.0,
            brake=0.20,
        ),
        sample(
            progress=0.22,
            elapsed=21.0,
            speed=150.0,
            brake=0.80,
            steering=2.0,
        ),
        sample(
            progress=0.24,
            elapsed=22.0,
            speed=135.0,
            brake=0.70,
            steering=6.0,
        ),
        sample(
            progress=0.26,
            elapsed=24.0,
            speed=120.0,
            brake=0.40,
            steering=12.0,
        ),
        sample(
            progress=0.28,
            elapsed=26.0,
            speed=105.0,
            steering=18.0,
        ),
        sample(
            progress=0.30,
            elapsed=28.0,
            speed=100.0,
            throttle=0.10,
            steering=20.0,
        ),
        sample(
            progress=0.32,
            elapsed=30.0,
            speed=105.0,
            throttle=0.30,
            steering=18.0,
        ),
        sample(
            progress=0.40,
            elapsed=40.0,
            speed=150.0,
            throttle=1.0,
        ),
        sample(
            progress=0.60,
            elapsed=60.0,
            speed=170.0,
            brake=0.30,
        ),
        sample(
            progress=0.62,
            elapsed=61.0,
            speed=155.0,
            brake=0.80,
            steering=-7.0,
        ),
        sample(
            progress=0.64,
            elapsed=63.0,
            speed=135.0,
            brake=0.30,
            steering=-14.0,
        ),
        sample(
            progress=0.66,
            elapsed=65.0,
            speed=120.0,
            steering=-19.0,
        ),
        sample(
            progress=0.68,
            elapsed=67.0,
            speed=115.0,
            throttle=0.10,
            steering=-21.0,
        ),
        sample(
            progress=0.70,
            elapsed=69.0,
            speed=120.0,
            throttle=0.30,
            steering=-18.0,
        ),
        sample(
            progress=0.80,
            elapsed=80.0,
            speed=160.0,
            throttle=1.0,
        ),
    )


def build_zones() -> tuple[
    BrakingZone,
    ...,
]:
    return (
        braking_zone(
            zone_number=1,
            start=0.20,
            end=0.26,
            start_elapsed=20.0,
            end_elapsed=24.0,
        ),
        braking_zone(
            zone_number=2,
            start=0.60,
            end=0.64,
            start_elapsed=60.0,
            end_elapsed=63.0,
        ),
    )


def test_detects_two_corner_entries() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    entries = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )

    assert len(
        entries
    ) == 2

    assert (
        entries[0].entry_number
        == 1
    )

    assert (
        entries[1].entry_number
        == 2
    )


def test_links_entry_to_braking_zone() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    entries = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )

    assert (
        entries[0]
        .source_braking_zone_number
        == 1
    )

    assert (
        entries[1]
        .source_braking_zone_number
        == 2
    )


def test_detects_turn_in() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.turn_in_progress
        == pytest.approx(
            0.24
        )
    )

    assert (
        first.turn_in_elapsed_seconds
        == pytest.approx(
            22.0
        )
    )

    assert (
        first.steering_at_turn_in_deg
        == pytest.approx(
            6.0
        )
    )


def test_detects_apex_proxy_from_minimum_speed() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.apex_progress
        == pytest.approx(
            0.30
        )
    )

    assert (
        first.apex_elapsed_seconds
        == pytest.approx(
            28.0
        )
    )

    assert (
        first.apex_speed_kmh
        == pytest.approx(
            100.0
        )
    )


def test_calculates_entry_speed_loss() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.entry_speed_kmh
        == pytest.approx(
            135.0
        )
    )

    assert (
        first.apex_speed_kmh
        == pytest.approx(
            100.0
        )
    )

    assert (
        first.speed_loss_kmh
        == pytest.approx(
            35.0
        )
    )


def test_calculates_brake_overlap() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.turn_in_before_brake_release
        is True
    )

    assert (
        first.brake_overlap_seconds
        == pytest.approx(
            2.0
        )
    )

    assert (
        first.brake_at_turn_in
        == pytest.approx(
            0.70
        )
    )


def test_calculates_entry_duration() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.entry_duration_seconds
        == pytest.approx(
            6.0
        )
    )

    assert (
        first.progress_to_apex
        == pytest.approx(
            0.06
        )
    )


def test_calculates_steering_metrics() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.maximum_abs_steering_deg
        == pytest.approx(
            20.0
        )
    )

    assert (
        first.average_abs_steering_deg
        == pytest.approx(
            14.0
        )
    )

    assert (
        first.sample_count
        == 4
    )


def test_preserves_steering_direction_at_turn_in() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    second = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[1]

    assert (
        second.steering_at_turn_in_deg
        == pytest.approx(
            -7.0
        )
    )


def test_calculates_throttle_transition() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.throttle_at_turn_in
        == pytest.approx(
            0.0
        )
    )

    assert (
        first.throttle_at_apex
        == pytest.approx(
            0.10
        )
    )


def test_custom_steering_threshold_changes_turn_in() -> None:
    service = (
        AssettoCorsaCornerEntryService(
            steering_threshold_deg=10.0
        )
    )

    first = service.analyze(
        samples=build_trace(),
        braking_zones=build_zones(),
    )[0]

    assert (
        first.turn_in_progress
        == pytest.approx(
            0.26
        )
    )

    assert (
        first.steering_at_turn_in_deg
        == pytest.approx(
            12.0
        )
    )


def test_zone_without_steering_is_ignored() -> None:
    trace = (
        sample(
            progress=0.20,
            elapsed=20.0,
            speed=150.0,
            brake=0.8,
        ),
        sample(
            progress=0.25,
            elapsed=25.0,
            speed=120.0,
            brake=0.3,
        ),
        sample(
            progress=0.30,
            elapsed=30.0,
            speed=110.0,
        ),
    )

    zone = braking_zone(
        zone_number=1,
        start=0.20,
        end=0.25,
        start_elapsed=20.0,
        end_elapsed=25.0,
    )

    service = (
        AssettoCorsaCornerEntryService()
    )

    entries = service.analyze(
        samples=trace,
        braking_zones=(
            zone,
        ),
    )

    assert entries == ()


def test_empty_samples_return_empty_tuple() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    assert (
        service.analyze(
            samples=(),
            braking_zones=build_zones(),
        )
        == ()
    )


def test_empty_braking_zones_return_empty_tuple() -> None:
    service = (
        AssettoCorsaCornerEntryService()
    )

    assert (
        service.analyze(
            samples=build_trace(),
            braking_zones=(),
        )
        == ()
    )


def test_rejects_invalid_steering_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="steering_threshold_deg",
    ):
        AssettoCorsaCornerEntryService(
            steering_threshold_deg=0.0
        )


def test_rejects_invalid_lookahead() -> None:
    with pytest.raises(
        ValueError,
        match="lookahead_progress",
    ):
        AssettoCorsaCornerEntryService(
            lookahead_progress=0.0
        )


def test_rejects_invalid_minimum_samples() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_samples",
    ):
        AssettoCorsaCornerEntryService(
            minimum_samples=1
        )


def test_rejects_decreasing_trace_progress() -> None:
    trace = (
        sample(
            progress=0.30,
            elapsed=20.0,
            speed=120.0,
        ),
        sample(
            progress=0.20,
            elapsed=21.0,
            speed=110.0,
        ),
    )

    service = (
        AssettoCorsaCornerEntryService()
    )

    with pytest.raises(
        ValueError,
        match="progress",
    ):
        service.analyze(
            samples=trace,
            braking_zones=build_zones(),
        )