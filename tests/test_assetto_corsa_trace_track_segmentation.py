import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    BrakingZone,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    CornerEntry,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit import (
    CornerExit,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation import (
    AssettoCorsaTrackSegmentationService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation_comparison import (
    AssettoCorsaTrackSegmentationComparisonService,
)


def braking_zone(
    *,
    number: int,
    start: float,
    end: float,
    minimum_speed: float,
) -> BrakingZone:
    return BrakingZone(
        zone_number=number,
        start_progress=start,
        end_progress=end,
        start_elapsed_seconds=(
            start * 100.0
        ),
        end_elapsed_seconds=(
            end * 100.0
        ),
        duration_seconds=(
            (end - start) * 100.0
        ),
        entry_speed_kmh=160.0,
        minimum_speed_kmh=(
            minimum_speed
        ),
        exit_speed_kmh=(
            minimum_speed + 10.0
        ),
        peak_brake=0.9,
        average_brake=0.6,
        sample_count=10,
    )


def corner_entry(
    *,
    number: int,
    braking_number: int,
    turn_in: float,
    apex: float,
    apex_speed: float,
) -> CornerEntry:
    return CornerEntry(
        entry_number=number,
        source_braking_zone_number=(
            braking_number
        ),
        braking_start_progress=(
            turn_in - 0.04
        ),
        brake_release_progress=(
            turn_in + 0.02
        ),
        turn_in_progress=turn_in,
        apex_progress=apex,
        turn_in_elapsed_seconds=(
            turn_in * 100.0
        ),
        brake_release_elapsed_seconds=(
            (turn_in + 0.02) * 100.0
        ),
        apex_elapsed_seconds=(
            apex * 100.0
        ),
        entry_duration_seconds=(
            (apex - turn_in) * 100.0
        ),
        brake_overlap_seconds=2.0,
        entry_speed_kmh=135.0,
        apex_speed_kmh=apex_speed,
        speed_loss_kmh=(
            135.0 - apex_speed
        ),
        brake_at_turn_in=0.6,
        throttle_at_turn_in=0.0,
        throttle_at_apex=0.1,
        steering_at_turn_in_deg=6.0,
        maximum_abs_steering_deg=20.0,
        average_abs_steering_deg=14.0,
        sample_count=10,
    )


def corner_exit(
    *,
    number: int,
    entry_number: int,
    apex: float,
    throttle_progress: float,
    exit_progress: float,
    apex_speed: float,
    exit_speed: float,
) -> CornerExit:
    return CornerExit(
        exit_number=number,
        source_entry_number=(
            entry_number
        ),
        apex_progress=apex,
        exit_progress=exit_progress,
        apex_elapsed_seconds=(
            apex * 100.0
        ),
        exit_elapsed_seconds=(
            exit_progress * 100.0
        ),
        duration_seconds=(
            (
                exit_progress
                - apex
            )
            * 100.0
        ),
        throttle_application_progress=(
            throttle_progress
        ),
        throttle_application_elapsed_seconds=(
            throttle_progress
            * 100.0
        ),
        time_to_throttle_seconds=(
            (
                throttle_progress
                - apex
            )
            * 100.0
        ),
        apex_speed_kmh=apex_speed,
        exit_speed_kmh=exit_speed,
        speed_gain_kmh=(
            exit_speed
            - apex_speed
        ),
        throttle_at_apex=0.1,
        throttle_at_exit=0.9,
        steering_at_apex_deg=20.0,
        steering_at_exit_deg=5.0,
        maximum_abs_steering_deg=20.0,
        average_abs_steering_deg=12.0,
        steering_unwind_deg=15.0,
        sample_count=10,
    )


def build_reference_components():
    zones = (
        braking_zone(
            number=10,
            start=0.20,
            end=0.26,
            minimum_speed=100.0,
        ),
        braking_zone(
            number=20,
            start=0.60,
            end=0.64,
            minimum_speed=115.0,
        ),
    )

    entries = (
        corner_entry(
            number=100,
            braking_number=10,
            turn_in=0.24,
            apex=0.30,
            apex_speed=100.0,
        ),
        corner_entry(
            number=200,
            braking_number=20,
            turn_in=0.62,
            apex=0.68,
            apex_speed=115.0,
        ),
    )

    exits = (
        corner_exit(
            number=1000,
            entry_number=100,
            apex=0.30,
            throttle_progress=0.32,
            exit_progress=0.38,
            apex_speed=100.0,
            exit_speed=132.0,
        ),
        corner_exit(
            number=2000,
            entry_number=200,
            apex=0.68,
            throttle_progress=0.70,
            exit_progress=0.76,
            apex_speed=115.0,
            exit_speed=145.0,
        ),
    )

    return (
        zones,
        entries,
        exits,
    )


def test_builds_complete_track_corners() -> None:
    (
        zones,
        entries,
        exits,
    ) = build_reference_components()

    result = (
        AssettoCorsaTrackSegmentationService()
        .segment(
            braking_zones=zones,
            entries=entries,
            exits=exits,
        )
    )

    assert result.corner_count == 2
    assert result.is_complete is True

    first = result.corners[0]

    assert first.corner_number == 1
    assert first.braking_zone_number == 10
    assert first.entry_number == 100
    assert first.exit_number == 1000

    assert (
        first.start_progress
        == pytest.approx(
            0.20
        )
    )

    assert (
        first.turn_in_progress
        == pytest.approx(
            0.24
        )
    )

    assert (
        first.apex_progress
        == pytest.approx(
            0.30
        )
    )

    assert (
        first.exit_progress
        == pytest.approx(
            0.38
        )
    )


def test_numbers_corners_by_track_order() -> None:
    (
        zones,
        entries,
        exits,
    ) = build_reference_components()

    result = (
        AssettoCorsaTrackSegmentationService()
        .segment(
            braking_zones=(
                zones[1],
                zones[0],
            ),
            entries=(
                entries[1],
                entries[0],
            ),
            exits=(
                exits[1],
                exits[0],
            ),
        )
    )

    assert [
        corner.apex_progress
        for corner in result.corners
    ] == [
        pytest.approx(
            0.30
        ),
        pytest.approx(
            0.68
        ),
    ]

    assert [
        corner.corner_number
        for corner in result.corners
    ] == [
        1,
        2,
    ]


def test_reports_incomplete_components() -> None:
    (
        zones,
        entries,
        exits,
    ) = build_reference_components()

    result = (
        AssettoCorsaTrackSegmentationService()
        .segment(
            braking_zones=zones,
            entries=entries,
            exits=(
                exits[0],
            ),
        )
    )

    assert result.corner_count == 1

    assert (
        result.unmatched_braking_zone_numbers
        == (
            20,
        )
    )

    assert (
        result.unmatched_entry_numbers
        == (
            200,
        )
    )


def test_rejects_duplicate_braking_link() -> None:
    zone = braking_zone(
        number=10,
        start=0.20,
        end=0.26,
        minimum_speed=100.0,
    )

    first = corner_entry(
        number=100,
        braking_number=10,
        turn_in=0.24,
        apex=0.30,
        apex_speed=100.0,
    )

    second = corner_entry(
        number=200,
        braking_number=10,
        turn_in=0.25,
        apex=0.31,
        apex_speed=99.0,
    )

    service = (
        AssettoCorsaTrackSegmentationService()
    )

    with pytest.raises(
        ValueError,
        match="same braking zone",
    ):
        service.segment(
            braking_zones=(
                zone,
            ),
            entries=(
                first,
                second,
            ),
            exits=(),
        )


def test_rejects_inconsistent_apex_link() -> None:
    zone = braking_zone(
        number=10,
        start=0.20,
        end=0.26,
        minimum_speed=100.0,
    )

    entry_value = corner_entry(
        number=100,
        braking_number=10,
        turn_in=0.24,
        apex=0.30,
        apex_speed=100.0,
    )

    exit_value = corner_exit(
        number=1000,
        entry_number=100,
        apex=0.40,
        throttle_progress=0.42,
        exit_progress=0.48,
        apex_speed=100.0,
        exit_speed=130.0,
    )

    service = (
        AssettoCorsaTrackSegmentationService(
            apex_link_tolerance=0.02
        )
    )

    with pytest.raises(
        ValueError,
        match="apex",
    ):
        service.segment(
            braking_zones=(
                zone,
            ),
            entries=(
                entry_value,
            ),
            exits=(
                exit_value,
            ),
        )


def point(
    *,
    progress: float,
    delta: float,
) -> AlignedTracePoint:
    return AlignedTracePoint(
        progress=progress,
        reference_elapsed_seconds=0.0,
        target_elapsed_seconds=delta,
        time_delta_seconds=delta,
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


def comparison() -> LapTraceComparison:
    return LapTraceComparison(
        reference_lap_number=2,
        target_lap_number=5,
        start_progress=0.0,
        end_progress=1.0,
        points=(
            point(
                progress=0.20,
                delta=0.05,
            ),
            point(
                progress=0.30,
                delta=0.25,
            ),
            point(
                progress=0.38,
                delta=0.40,
            ),
            point(
                progress=0.60,
                delta=0.45,
            ),
            point(
                progress=0.68,
                delta=0.35,
            ),
            point(
                progress=0.76,
                delta=0.30,
            ),
            point(
                progress=1.0,
                delta=0.30,
            ),
        ),
        final_time_delta_seconds=0.30,
        average_speed_delta_kmh=0.0,
        largest_speed_loss_progress=None,
        largest_speed_gain_progress=None,
    )


def build_target_components():
    zones = (
        braking_zone(
            number=70,
            start=0.18,
            end=0.27,
            minimum_speed=94.0,
        ),
        braking_zone(
            number=80,
            start=0.61,
            end=0.65,
            minimum_speed=118.0,
        ),
    )

    entries = (
        corner_entry(
            number=700,
            braking_number=70,
            turn_in=0.22,
            apex=0.31,
            apex_speed=94.0,
        ),
        corner_entry(
            number=800,
            braking_number=80,
            turn_in=0.63,
            apex=0.69,
            apex_speed=118.0,
        ),
    )

    exits = (
        corner_exit(
            number=7000,
            entry_number=700,
            apex=0.31,
            throttle_progress=0.35,
            exit_progress=0.40,
            apex_speed=94.0,
            exit_speed=126.0,
        ),
        corner_exit(
            number=8000,
            entry_number=800,
            apex=0.69,
            throttle_progress=0.70,
            exit_progress=0.77,
            apex_speed=118.0,
            exit_speed=148.0,
        ),
    )

    return (
        zones,
        entries,
        exits,
    )


def segment_reference():
    (
        zones,
        entries,
        exits,
    ) = build_reference_components()

    return (
        AssettoCorsaTrackSegmentationService()
        .segment(
            braking_zones=zones,
            entries=entries,
            exits=exits,
        )
    )


def segment_target():
    (
        zones,
        entries,
        exits,
    ) = build_target_components()

    return (
        AssettoCorsaTrackSegmentationService()
        .segment(
            braking_zones=zones,
            entries=entries,
            exits=exits,
        )
    )


def test_compares_complete_corners() -> None:
    reference = segment_reference()
    target = segment_target()

    result = (
        AssettoCorsaTrackSegmentationComparisonService()
        .compare(
            reference_corners=(
                reference.corners
            ),
            target_corners=(
                target.corners
            ),
            trace_comparison=(
                comparison()
            ),
        )
    )

    assert (
        result.matched_corner_count
        == 2
    )

    first = result.corners[0]

    assert (
        first.braking_start_progress_delta
        == pytest.approx(
            -0.02
        )
    )

    assert (
        first.turn_in_progress_delta
        == pytest.approx(
            -0.02
        )
    )

    assert (
        first.apex_speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )

    assert (
        first.exit_speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )


def test_splits_corner_time_loss_by_phase() -> None:
    reference = segment_reference()
    target = segment_target()

    result = (
        AssettoCorsaTrackSegmentationComparisonService()
        .compare(
            reference_corners=(
                reference.corners
            ),
            target_corners=(
                target.corners
            ),
            trace_comparison=(
                comparison()
            ),
        )
    )

    first = result.corners[0]

    assert (
        first.time_delta_at_start_seconds
        == pytest.approx(
            0.05
        )
    )

    assert (
        first.time_delta_at_apex_seconds
        == pytest.approx(
            0.25
        )
    )

    assert (
        first.time_delta_at_exit_seconds
        == pytest.approx(
            0.40
        )
    )

    assert (
        first
        .time_delta_to_apex_change_seconds
        == pytest.approx(
            0.20
        )
    )

    assert (
        first.time_delta_exit_change_seconds
        == pytest.approx(
            0.15
        )
    )

    assert (
        first.time_delta_total_change_seconds
        == pytest.approx(
            0.35
        )
    )

    assert (
        first.time_lost_seconds
        == pytest.approx(
            0.35
        )
    )

    assert (
        first.entry_time_loss_seconds
        == pytest.approx(
            0.20
        )
    )

    assert (
        first.exit_time_loss_seconds
        == pytest.approx(
            0.15
        )
    )


def test_second_corner_can_gain_time() -> None:
    reference = segment_reference()
    target = segment_target()

    result = (
        AssettoCorsaTrackSegmentationComparisonService()
        .compare(
            reference_corners=(
                reference.corners
            ),
            target_corners=(
                target.corners
            ),
            trace_comparison=(
                comparison()
            ),
        )
    )

    second = result.corners[1]

    assert (
        second.time_lost_seconds
        == pytest.approx(
            0.0
        )
    )

    assert (
        second.time_gained_seconds
        == pytest.approx(
            0.15
        )
    )


def test_rejects_invalid_matching_distance() -> None:
    with pytest.raises(
        ValueError,
        match="maximum_apex_distance",
    ):
        AssettoCorsaTrackSegmentationComparisonService(
            maximum_apex_distance=0.0
        )