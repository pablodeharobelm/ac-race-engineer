import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    BrakingZone,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking_comparison import (
    AssettoCorsaBrakingComparisonService,
)


def braking_zone(
    *,
    zone_number: int,
    start: float,
    end: float,
    duration: float,
    entry_speed: float,
    minimum_speed: float,
    exit_speed: float,
    peak_brake: float,
    average_brake: float,
) -> BrakingZone:
    return BrakingZone(
        zone_number=zone_number,
        start_progress=start,
        end_progress=end,
        start_elapsed_seconds=0.0,
        end_elapsed_seconds=duration,
        duration_seconds=duration,
        entry_speed_kmh=entry_speed,
        minimum_speed_kmh=minimum_speed,
        exit_speed_kmh=exit_speed,
        peak_brake=peak_brake,
        average_brake=average_brake,
        sample_count=10,
    )


def aligned_point(
    *,
    progress: float,
    time_delta: float,
) -> AlignedTracePoint:
    return AlignedTracePoint(
        progress=progress,
        reference_elapsed_seconds=0.0,
        target_elapsed_seconds=(
            time_delta
        ),
        time_delta_seconds=(
            time_delta
        ),
        reference_speed_kmh=0.0,
        target_speed_kmh=0.0,
        speed_delta_kmh=0.0,
        reference_throttle=0.0,
        target_throttle=0.0,
        throttle_delta=0.0,
        reference_brake=0.0,
        target_brake=0.0,
        brake_delta=0.0,
        reference_steering_angle_deg=0.0,
        target_steering_angle_deg=0.0,
        steering_delta_deg=0.0,
    )


def trace_comparison() -> LapTraceComparison:
    return LapTraceComparison(
        reference_lap_number=2,
        target_lap_number=5,
        start_progress=0.0,
        end_progress=1.0,
        points=(
            aligned_point(
                progress=0.0,
                time_delta=0.0,
            ),
            aligned_point(
                progress=0.20,
                time_delta=0.10,
            ),
            aligned_point(
                progress=0.30,
                time_delta=0.40,
            ),
            aligned_point(
                progress=0.60,
                time_delta=0.50,
            ),
            aligned_point(
                progress=0.70,
                time_delta=0.30,
            ),
            aligned_point(
                progress=1.0,
                time_delta=0.30,
            ),
        ),
        final_time_delta_seconds=0.30,
        average_speed_delta_kmh=0.0,
        largest_speed_loss_progress=None,
        largest_speed_gain_progress=None,
    )


def reference_zones() -> tuple[
    BrakingZone,
    ...,
]:
    return (
        braking_zone(
            zone_number=1,
            start=0.20,
            end=0.30,
            duration=3.0,
            entry_speed=160.0,
            minimum_speed=100.0,
            exit_speed=110.0,
            peak_brake=0.90,
            average_brake=0.60,
        ),
        braking_zone(
            zone_number=2,
            start=0.60,
            end=0.70,
            duration=2.5,
            entry_speed=170.0,
            minimum_speed=120.0,
            exit_speed=130.0,
            peak_brake=0.80,
            average_brake=0.50,
        ),
    )


def target_zones() -> tuple[
    BrakingZone,
    ...,
]:
    return (
        braking_zone(
            zone_number=7,
            start=0.18,
            end=0.29,
            duration=3.2,
            entry_speed=158.0,
            minimum_speed=95.0,
            exit_speed=105.0,
            peak_brake=1.00,
            average_brake=0.70,
        ),
        braking_zone(
            zone_number=8,
            start=0.62,
            end=0.72,
            duration=2.2,
            entry_speed=172.0,
            minimum_speed=123.0,
            exit_speed=135.0,
            peak_brake=0.75,
            average_brake=0.45,
        ),
    )


def test_matches_zones_by_track_position() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.matched_zone_count
        == 2
    )

    assert (
        result.zones[0]
        .reference_zone_number
        == 1
    )

    assert (
        result.zones[0]
        .target_zone_number
        == 7
    )

    assert (
        result.zones[1]
        .reference_zone_number
        == 2
    )

    assert (
        result.zones[1]
        .target_zone_number
        == 8
    )


def test_calculates_braking_position_deltas() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    )

    first = result.zones[0]

    assert (
        first.start_progress_delta
        == pytest.approx(
            -0.02
        )
    )

    assert (
        first.end_progress_delta
        == pytest.approx(
            -0.01
        )
    )

    assert (
        first.target_brakes_earlier
        is True
    )

    assert (
        first.target_brakes_later
        is False
    )

    assert (
        first.target_releases_brake_earlier
        is True
    )


def test_calculates_duration_delta() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    first = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    ).zones[0]

    assert (
        first.duration_delta_seconds
        == pytest.approx(
            0.2
        )
    )


def test_calculates_speed_deltas() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    first = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    ).zones[0]

    assert (
        first.entry_speed_delta_kmh
        == pytest.approx(
            -2.0
        )
    )

    assert (
        first.minimum_speed_delta_kmh
        == pytest.approx(
            -5.0
        )
    )

    assert (
        first.exit_speed_delta_kmh
        == pytest.approx(
            -5.0
        )
    )


def test_calculates_brake_input_deltas() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    first = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    ).zones[0]

    assert (
        first.peak_brake_delta
        == pytest.approx(
            0.10
        )
    )

    assert (
        first.average_brake_delta
        == pytest.approx(
            0.10
        )
    )


def test_calculates_time_lost_through_zone() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    first = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    ).zones[0]

    assert (
        first.time_delta_at_start_seconds
        == pytest.approx(
            0.10
        )
    )

    assert (
        first.time_delta_at_end_seconds
        == pytest.approx(
            0.40
        )
    )

    assert (
        first.time_delta_change_seconds
        == pytest.approx(
            0.30
        )
    )

    assert (
        first.time_lost_seconds
        == pytest.approx(
            0.30
        )
    )

    assert (
        first.time_gained_seconds
        == pytest.approx(
            0.0
        )
    )


def test_calculates_time_gained_through_zone() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    second = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    ).zones[1]

    assert (
        second.time_delta_at_start_seconds
        == pytest.approx(
            0.50
        )
    )

    assert (
        second.time_delta_at_end_seconds
        == pytest.approx(
            0.30
        )
    )

    assert (
        second.time_delta_change_seconds
        == pytest.approx(
            -0.20
        )
    )

    assert (
        second.time_gained_seconds
        == pytest.approx(
            0.20
        )
    )

    assert (
        second.time_lost_seconds
        == pytest.approx(
            0.0
        )
    )


def test_total_time_gain_and_loss() -> None:
    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference_zones(),
        target_zones=target_zones(),
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.total_time_lost_seconds
        == pytest.approx(
            0.30
        )
    )

    assert (
        result.total_time_gained_seconds
        == pytest.approx(
            0.20
        )
    )


def test_reports_unmatched_zones() -> None:
    extra_target = braking_zone(
        zone_number=99,
        start=0.90,
        end=0.94,
        duration=1.0,
        entry_speed=150.0,
        minimum_speed=120.0,
        exit_speed=125.0,
        peak_brake=0.6,
        average_brake=0.4,
    )

    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference_zones(),
        target_zones=(
            *target_zones(),
            extra_target,
        ),
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.unmatched_reference_zones
        == ()
    )

    assert (
        result.unmatched_target_zones
        == (
            99,
        )
    )


def test_matches_shifted_zone_using_center_distance() -> None:
    reference = (
        braking_zone(
            zone_number=1,
            start=0.20,
            end=0.22,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    target = (
        braking_zone(
            zone_number=2,
            start=0.23,
            end=0.25,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    service = (
        AssettoCorsaBrakingComparisonService(
            maximum_center_distance=0.05
        )
    )

    result = service.compare(
        reference_zones=reference,
        target_zones=target,
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.matched_zone_count
        == 1
    )


def test_does_not_match_distant_zones() -> None:
    reference = (
        braking_zone(
            zone_number=1,
            start=0.10,
            end=0.15,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    target = (
        braking_zone(
            zone_number=2,
            start=0.80,
            end=0.85,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference,
        target_zones=target,
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.matched_zone_count
        == 0
    )

    assert (
        result.unmatched_reference_zones
        == (
            1,
        )
    )

    assert (
        result.unmatched_target_zones
        == (
            2,
        )
    )


def test_interpolates_time_delta() -> None:
    reference = (
        braking_zone(
            zone_number=1,
            start=0.25,
            end=0.275,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    target = (
        braking_zone(
            zone_number=2,
            start=0.25,
            end=0.275,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference,
        target_zones=target,
        trace_comparison=(
            trace_comparison()
        ),
    )

    zone = result.zones[0]

    assert (
        zone.time_delta_at_start_seconds
        == pytest.approx(
            0.25
        )
    )

    assert (
        zone.time_delta_at_end_seconds
        == pytest.approx(
            0.325
        )
    )


def test_time_delta_is_none_outside_trace_overlap() -> None:
    reference = (
        braking_zone(
            zone_number=1,
            start=0.05,
            end=0.10,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    target = (
        braking_zone(
            zone_number=2,
            start=0.05,
            end=0.10,
            duration=1.0,
            entry_speed=150.0,
            minimum_speed=120.0,
            exit_speed=125.0,
            peak_brake=0.8,
            average_brake=0.5,
        ),
    )

    comparison = (
        trace_comparison()
    )

    partial = LapTraceComparison(
        reference_lap_number=(
            comparison.reference_lap_number
        ),
        target_lap_number=(
            comparison.target_lap_number
        ),
        start_progress=0.20,
        end_progress=1.0,
        points=(
            comparison.points[1:]
        ),
        final_time_delta_seconds=(
            comparison.final_time_delta_seconds
        ),
        average_speed_delta_kmh=(
            comparison.average_speed_delta_kmh
        ),
        largest_speed_loss_progress=(
            comparison
            .largest_speed_loss_progress
        ),
        largest_speed_gain_progress=(
            comparison
            .largest_speed_gain_progress
        ),
    )

    service = (
        AssettoCorsaBrakingComparisonService()
    )

    result = service.compare(
        reference_zones=reference,
        target_zones=target,
        trace_comparison=partial,
    )

    zone = result.zones[0]

    assert (
        zone.time_delta_at_start_seconds
        is None
    )

    assert (
        zone.time_delta_at_end_seconds
        is None
    )

    assert (
        zone.time_delta_change_seconds
        is None
    )

    assert (
        zone.time_lost_seconds
        is None
    )


def test_rejects_invalid_center_distance() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_center_distance",
    ):
        AssettoCorsaBrakingComparisonService(
            maximum_center_distance=0.0
        )


def test_rejects_invalid_overlap_ratio() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_overlap_ratio",
    ):
        AssettoCorsaBrakingComparisonService(
            minimum_overlap_ratio=1.1
        )