import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    CornerEntry,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_comparison import (
    AssettoCorsaCornerEntryComparisonService,
)


def corner_entry(
    *,
    entry_number: int,
    braking_zone_number: int,
    turn_in: float,
    apex: float,
    duration: float,
    brake_overlap: float,
    entry_speed: float,
    apex_speed: float,
    brake_at_turn_in: float,
    throttle_at_turn_in: float,
    throttle_at_apex: float,
    maximum_steering: float,
    average_steering: float,
) -> CornerEntry:
    return CornerEntry(
        entry_number=entry_number,
        source_braking_zone_number=(
            braking_zone_number
        ),
        braking_start_progress=(
            turn_in - 0.04
        ),
        brake_release_progress=(
            turn_in + 0.02
        ),
        turn_in_progress=turn_in,
        apex_progress=apex,
        turn_in_elapsed_seconds=0.0,
        brake_release_elapsed_seconds=(
            brake_overlap
        ),
        apex_elapsed_seconds=duration,
        entry_duration_seconds=duration,
        brake_overlap_seconds=(
            brake_overlap
        ),
        entry_speed_kmh=entry_speed,
        apex_speed_kmh=apex_speed,
        speed_loss_kmh=(
            entry_speed
            - apex_speed
        ),
        brake_at_turn_in=(
            brake_at_turn_in
        ),
        throttle_at_turn_in=(
            throttle_at_turn_in
        ),
        throttle_at_apex=(
            throttle_at_apex
        ),
        steering_at_turn_in_deg=5.0,
        maximum_abs_steering_deg=(
            maximum_steering
        ),
        average_abs_steering_deg=(
            average_steering
        ),
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
                progress=0.24,
                time_delta=0.10,
            ),
            aligned_point(
                progress=0.30,
                time_delta=0.37,
            ),
            aligned_point(
                progress=0.62,
                time_delta=0.50,
            ),
            aligned_point(
                progress=0.68,
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


def reference_entries() -> tuple[
    CornerEntry,
    ...,
]:
    return (
        corner_entry(
            entry_number=1,
            braking_zone_number=1,
            turn_in=0.24,
            apex=0.30,
            duration=6.0,
            brake_overlap=2.0,
            entry_speed=135.0,
            apex_speed=100.0,
            brake_at_turn_in=0.70,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.10,
            maximum_steering=20.0,
            average_steering=14.0,
        ),
        corner_entry(
            entry_number=2,
            braking_zone_number=2,
            turn_in=0.62,
            apex=0.68,
            duration=6.0,
            brake_overlap=2.0,
            entry_speed=145.0,
            apex_speed=115.0,
            brake_at_turn_in=0.60,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.10,
            maximum_steering=21.0,
            average_steering=15.0,
        ),
    )


def target_entries() -> tuple[
    CornerEntry,
    ...,
]:
    return (
        corner_entry(
            entry_number=7,
            braking_zone_number=7,
            turn_in=0.22,
            apex=0.31,
            duration=6.5,
            brake_overlap=2.4,
            entry_speed=132.0,
            apex_speed=94.0,
            brake_at_turn_in=0.80,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.05,
            maximum_steering=24.5,
            average_steering=17.0,
        ),
        corner_entry(
            entry_number=8,
            braking_zone_number=8,
            turn_in=0.63,
            apex=0.69,
            duration=5.8,
            brake_overlap=1.7,
            entry_speed=147.0,
            apex_speed=119.0,
            brake_at_turn_in=0.50,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.20,
            maximum_steering=19.0,
            average_steering=13.0,
        ),
    )


def test_matches_entries_by_track_position() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    result = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.matched_entry_count
        == 2
    )

    assert (
        result.entries[0]
        .reference_entry_number
        == 1
    )

    assert (
        result.entries[0]
        .target_entry_number
        == 7
    )

    assert (
        result.entries[1]
        .reference_entry_number
        == 2
    )

    assert (
        result.entries[1]
        .target_entry_number
        == 8
    )


def test_calculates_turn_in_delta() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.turn_in_progress_delta
        == pytest.approx(
            -0.02
        )
    )

    assert (
        first.target_turns_in_earlier
        is True
    )

    assert (
        first.target_turns_in_later
        is False
    )


def test_calculates_apex_position_delta() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.apex_progress_delta
        == pytest.approx(
            0.01
        )
    )

    assert (
        first.target_reaches_apex_later
        is True
    )


def test_calculates_entry_duration_delta() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.entry_duration_delta_seconds
        == pytest.approx(
            0.5
        )
    )


def test_calculates_brake_overlap_delta() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.brake_overlap_delta_seconds
        == pytest.approx(
            0.4
        )
    )


def test_calculates_speed_deltas() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.entry_speed_delta_kmh
        == pytest.approx(
            -3.0
        )
    )

    assert (
        first.apex_speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )

    assert (
        first.speed_loss_delta_kmh
        == pytest.approx(
            3.0
        )
    )


def test_calculates_brake_and_throttle_deltas() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.brake_at_turn_in_delta
        == pytest.approx(
            0.10
        )
    )

    assert (
        first.throttle_at_turn_in_delta
        == pytest.approx(
            0.0
        )
    )

    assert (
        first.throttle_at_apex_delta
        == pytest.approx(
            -0.05
        )
    )


def test_calculates_steering_deltas() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.maximum_abs_steering_delta_deg
        == pytest.approx(
            4.5
        )
    )

    assert (
        first.average_abs_steering_delta_deg
        == pytest.approx(
            3.0
        )
    )


def test_calculates_time_lost_during_entry() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    first = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[0]

    assert (
        first.time_delta_at_turn_in_seconds
        == pytest.approx(
            0.10
        )
    )

    assert (
        first.time_delta_at_apex_seconds
        == pytest.approx(
            0.37
        )
    )

    assert (
        first.time_delta_change_seconds
        == pytest.approx(
            0.27
        )
    )

    assert (
        first.time_lost_seconds
        == pytest.approx(
            0.27
        )
    )

    assert (
        first.time_gained_seconds
        == pytest.approx(
            0.0
        )
    )


def test_calculates_time_gained_during_entry() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    second = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    ).entries[1]

    assert (
        second.time_delta_at_turn_in_seconds
        == pytest.approx(
            0.50
        )
    )

    assert (
        second.time_delta_at_apex_seconds
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


def test_reports_total_gain_and_loss() -> None:
    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    result = service.compare(
        reference_entries=reference_entries(),
        target_entries=target_entries(),
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.total_time_lost_seconds
        == pytest.approx(
            0.27
        )
    )

    assert (
        result.total_time_gained_seconds
        == pytest.approx(
            0.20
        )
    )


def test_reports_unmatched_entry() -> None:
    extra_target = corner_entry(
        entry_number=99,
        braking_zone_number=99,
        turn_in=0.90,
        apex=0.94,
        duration=3.0,
        brake_overlap=1.0,
        entry_speed=120.0,
        apex_speed=100.0,
        brake_at_turn_in=0.5,
        throttle_at_turn_in=0.0,
        throttle_at_apex=0.2,
        maximum_steering=15.0,
        average_steering=10.0,
    )

    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    result = service.compare(
        reference_entries=reference_entries(),
        target_entries=(
            *target_entries(),
            extra_target,
        ),
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.unmatched_reference_entries
        == ()
    )

    assert (
        result.unmatched_target_entries
        == (
            99,
        )
    )


def test_does_not_match_distant_entries() -> None:
    reference = (
        corner_entry(
            entry_number=1,
            braking_zone_number=1,
            turn_in=0.10,
            apex=0.15,
            duration=2.0,
            brake_overlap=1.0,
            entry_speed=120.0,
            apex_speed=100.0,
            brake_at_turn_in=0.5,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.1,
            maximum_steering=15.0,
            average_steering=10.0,
        ),
    )

    target = (
        corner_entry(
            entry_number=2,
            braking_zone_number=2,
            turn_in=0.80,
            apex=0.85,
            duration=2.0,
            brake_overlap=1.0,
            entry_speed=120.0,
            apex_speed=100.0,
            brake_at_turn_in=0.5,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.1,
            maximum_steering=15.0,
            average_steering=10.0,
        ),
    )

    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    result = service.compare(
        reference_entries=reference,
        target_entries=target,
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.matched_entry_count
        == 0
    )

    assert (
        result.unmatched_reference_entries
        == (
            1,
        )
    )

    assert (
        result.unmatched_target_entries
        == (
            2,
        )
    )


def test_time_delta_is_interpolated() -> None:
    reference = (
        corner_entry(
            entry_number=1,
            braking_zone_number=1,
            turn_in=0.27,
            apex=0.285,
            duration=2.0,
            brake_overlap=1.0,
            entry_speed=120.0,
            apex_speed=100.0,
            brake_at_turn_in=0.5,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.1,
            maximum_steering=15.0,
            average_steering=10.0,
        ),
    )

    target = (
        corner_entry(
            entry_number=2,
            braking_zone_number=2,
            turn_in=0.27,
            apex=0.285,
            duration=2.0,
            brake_overlap=1.0,
            entry_speed=120.0,
            apex_speed=100.0,
            brake_at_turn_in=0.5,
            throttle_at_turn_in=0.0,
            throttle_at_apex=0.1,
            maximum_steering=15.0,
            average_steering=10.0,
        ),
    )

    service = (
        AssettoCorsaCornerEntryComparisonService()
    )

    result = service.compare(
        reference_entries=reference,
        target_entries=target,
        trace_comparison=(
            trace_comparison()
        ),
    )

    entry = result.entries[0]

    assert (
        entry.time_delta_at_turn_in_seconds
        == pytest.approx(
            0.235
        )
    )

    assert (
        entry.time_delta_at_apex_seconds
        == pytest.approx(
            0.3025
        )
    )


def test_rejects_invalid_center_distance() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_center_distance",
    ):
        AssettoCorsaCornerEntryComparisonService(
            maximum_center_distance=0.0
        )


def test_rejects_invalid_overlap_ratio() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_overlap_ratio",
    ):
        AssettoCorsaCornerEntryComparisonService(
            minimum_overlap_ratio=1.1
        )