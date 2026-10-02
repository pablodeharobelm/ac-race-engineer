import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    DrivingTraceSample,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    CornerEntry,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit import (
    AssettoCorsaCornerExitService,
    CornerExit,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_comparison import (
    AssettoCorsaCornerExitComparisonService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_diagnostics import (
    AssettoCorsaCornerExitDiagnosticService,
    CornerExitDiagnosticCode,
    CornerExitDiagnosticSeverity,
)


def sample(
    *,
    progress: float,
    elapsed: float,
    speed: float,
    throttle: float,
    steering: float,
) -> DrivingTraceSample:
    return DrivingTraceSample(
        progress=progress,
        elapsed_seconds=elapsed,
        speed_kmh=speed,
        throttle=throttle,
        brake=0.0,
        steering_angle_deg=steering,
    )


def entry() -> CornerEntry:
    return CornerEntry(
        entry_number=1,
        source_braking_zone_number=1,
        braking_start_progress=0.20,
        brake_release_progress=0.26,
        turn_in_progress=0.24,
        apex_progress=0.30,
        turn_in_elapsed_seconds=22.0,
        brake_release_elapsed_seconds=24.0,
        apex_elapsed_seconds=28.0,
        entry_duration_seconds=6.0,
        brake_overlap_seconds=2.0,
        entry_speed_kmh=135.0,
        apex_speed_kmh=100.0,
        speed_loss_kmh=35.0,
        brake_at_turn_in=0.7,
        throttle_at_turn_in=0.0,
        throttle_at_apex=0.1,
        steering_at_turn_in_deg=6.0,
        maximum_abs_steering_deg=20.0,
        average_abs_steering_deg=14.0,
        sample_count=4,
    )


def exit_trace() -> tuple[
    DrivingTraceSample,
    ...,
]:
    return (
        sample(
            progress=0.30,
            elapsed=28.0,
            speed=100.0,
            throttle=0.10,
            steering=20.0,
        ),
        sample(
            progress=0.32,
            elapsed=29.0,
            speed=104.0,
            throttle=0.20,
            steering=18.0,
        ),
        sample(
            progress=0.34,
            elapsed=30.0,
            speed=110.0,
            throttle=0.40,
            steering=14.0,
        ),
        sample(
            progress=0.36,
            elapsed=31.0,
            speed=120.0,
            throttle=0.70,
            steering=9.0,
        ),
        sample(
            progress=0.38,
            elapsed=32.0,
            speed=132.0,
            throttle=0.85,
            steering=6.0,
        ),
        sample(
            progress=0.40,
            elapsed=33.0,
            speed=142.0,
            throttle=1.00,
            steering=3.0,
        ),
    )


def test_detects_corner_exit() -> None:
    service = (
        AssettoCorsaCornerExitService()
    )

    exits = service.analyze(
        samples=exit_trace(),
        entries=(
            entry(),
        ),
    )

    assert len(
        exits
    ) == 1

    corner_exit = exits[0]

    assert (
        corner_exit.apex_progress
        == pytest.approx(
            0.30
        )
    )

    assert (
        corner_exit.exit_progress
        == pytest.approx(
            0.38
        )
    )


def test_detects_throttle_application() -> None:
    service = (
        AssettoCorsaCornerExitService()
    )

    corner_exit = service.analyze(
        samples=exit_trace(),
        entries=(
            entry(),
        ),
    )[0]

    assert (
        corner_exit
        .throttle_application_progress
        == pytest.approx(
            0.32
        )
    )

    assert (
        corner_exit
        .time_to_throttle_seconds
        == pytest.approx(
            1.0
        )
    )


def test_corner_exit_speed_and_steering() -> None:
    service = (
        AssettoCorsaCornerExitService()
    )

    corner_exit = service.analyze(
        samples=exit_trace(),
        entries=(
            entry(),
        ),
    )[0]

    assert (
        corner_exit.apex_speed_kmh
        == pytest.approx(
            100.0
        )
    )

    assert (
        corner_exit.exit_speed_kmh
        == pytest.approx(
            132.0
        )
    )

    assert (
        corner_exit.speed_gain_kmh
        == pytest.approx(
            32.0
        )
    )

    assert (
        corner_exit.steering_unwind_deg
        == pytest.approx(
            14.0
        )
    )


def corner_exit(
    *,
    exit_number: int,
    apex: float,
    exit_progress: float,
    throttle_progress: float,
    time_to_throttle: float,
    exit_speed: float,
    throttle_at_exit: float,
    steering_at_exit: float,
    steering_unwind: float,
) -> CornerExit:
    return CornerExit(
        exit_number=exit_number,
        source_entry_number=exit_number,
        apex_progress=apex,
        exit_progress=exit_progress,
        apex_elapsed_seconds=0.0,
        exit_elapsed_seconds=4.0,
        duration_seconds=4.0,
        throttle_application_progress=(
            throttle_progress
        ),
        throttle_application_elapsed_seconds=(
            time_to_throttle
        ),
        time_to_throttle_seconds=(
            time_to_throttle
        ),
        apex_speed_kmh=100.0,
        exit_speed_kmh=exit_speed,
        speed_gain_kmh=(
            exit_speed - 100.0
        ),
        throttle_at_apex=0.1,
        throttle_at_exit=(
            throttle_at_exit
        ),
        steering_at_apex_deg=20.0,
        steering_at_exit_deg=(
            steering_at_exit
        ),
        maximum_abs_steering_deg=20.0,
        average_abs_steering_deg=12.0,
        steering_unwind_deg=(
            steering_unwind
        ),
        sample_count=5,
    )


def point(
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
            point(
                progress=0.30,
                time_delta=0.10,
            ),
            point(
                progress=0.38,
                time_delta=0.40,
            ),
            point(
                progress=1.0,
                time_delta=0.40,
            ),
        ),
        final_time_delta_seconds=0.40,
        average_speed_delta_kmh=0.0,
        largest_speed_loss_progress=None,
        largest_speed_gain_progress=None,
    )


def test_compares_corner_exits() -> None:
    reference = (
        corner_exit(
            exit_number=1,
            apex=0.30,
            exit_progress=0.38,
            throttle_progress=0.32,
            time_to_throttle=1.0,
            exit_speed=132.0,
            throttle_at_exit=0.90,
            steering_at_exit=5.0,
            steering_unwind=15.0,
        ),
    )

    target = (
        corner_exit(
            exit_number=7,
            apex=0.31,
            exit_progress=0.40,
            throttle_progress=0.35,
            time_to_throttle=1.4,
            exit_speed=126.0,
            throttle_at_exit=0.75,
            steering_at_exit=9.0,
            steering_unwind=11.0,
        ),
    )

    service = (
        AssettoCorsaCornerExitComparisonService()
    )

    result = service.compare(
        reference_exits=reference,
        target_exits=target,
        trace_comparison=(
            trace_comparison()
        ),
    )

    assert (
        result.matched_exit_count
        == 1
    )

    delta = result.exits[0]

    assert (
        delta
        .throttle_application_progress_delta
        == pytest.approx(
            0.03
        )
    )

    assert (
        delta.time_to_throttle_delta_seconds
        == pytest.approx(
            0.4
        )
    )

    assert (
        delta.exit_speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )

    assert (
        delta.throttle_at_exit_delta
        == pytest.approx(
            -0.15
        )
    )


def test_corner_exit_time_loss() -> None:
    service = (
        AssettoCorsaCornerExitComparisonService()
    )

    result = service.compare(
        reference_exits=(
            corner_exit(
                exit_number=1,
                apex=0.30,
                exit_progress=0.38,
                throttle_progress=0.32,
                time_to_throttle=1.0,
                exit_speed=132.0,
                throttle_at_exit=0.9,
                steering_at_exit=5.0,
                steering_unwind=15.0,
            ),
        ),
        target_exits=(
            corner_exit(
                exit_number=2,
                apex=0.31,
                exit_progress=0.40,
                throttle_progress=0.35,
                time_to_throttle=1.4,
                exit_speed=126.0,
                throttle_at_exit=0.75,
                steering_at_exit=9.0,
                steering_unwind=11.0,
            ),
        ),
        trace_comparison=(
            trace_comparison()
        ),
    )

    delta = result.exits[0]

    assert (
        delta.time_delta_at_apex_seconds
        == pytest.approx(
            0.10
        )
    )

    assert (
        delta.time_delta_at_exit_seconds
        == pytest.approx(
            0.40
        )
    )

    assert (
        delta.time_lost_seconds
        == pytest.approx(
            0.30
        )
    )


def test_diagnoses_bad_corner_exit() -> None:
    comparison_service = (
        AssettoCorsaCornerExitComparisonService()
    )

    comparison = (
        comparison_service.compare(
            reference_exits=(
                corner_exit(
                    exit_number=1,
                    apex=0.30,
                    exit_progress=0.38,
                    throttle_progress=0.32,
                    time_to_throttle=1.0,
                    exit_speed=132.0,
                    throttle_at_exit=0.90,
                    steering_at_exit=5.0,
                    steering_unwind=15.0,
                ),
            ),
            target_exits=(
                corner_exit(
                    exit_number=2,
                    apex=0.31,
                    exit_progress=0.40,
                    throttle_progress=0.35,
                    time_to_throttle=1.4,
                    exit_speed=126.0,
                    throttle_at_exit=0.75,
                    steering_at_exit=9.0,
                    steering_unwind=11.0,
                ),
            ),
            trace_comparison=(
                trace_comparison()
            ),
        )
    )

    diagnostic_service = (
        AssettoCorsaCornerExitDiagnosticService()
    )

    report = diagnostic_service.analyze(
        comparison
    )

    codes = {
        diagnostic.code
        for diagnostic
        in report.diagnostics
    }

    assert (
        CornerExitDiagnosticCode
        .LATE_THROTTLE_APPLICATION
        in codes
    )

    assert (
        CornerExitDiagnosticCode
        .POOR_EXIT_SPEED
        in codes
    )

    assert (
        CornerExitDiagnosticCode
        .LOW_EXIT_THROTTLE
        in codes
    )

    assert (
        CornerExitDiagnosticCode
        .SLOW_STEERING_UNWIND
        in codes
    )


def test_corner_exit_severity() -> None:
    comparison_service = (
        AssettoCorsaCornerExitComparisonService()
    )

    comparison = (
        comparison_service.compare(
            reference_exits=(
                corner_exit(
                    exit_number=1,
                    apex=0.30,
                    exit_progress=0.38,
                    throttle_progress=0.32,
                    time_to_throttle=1.0,
                    exit_speed=132.0,
                    throttle_at_exit=0.90,
                    steering_at_exit=5.0,
                    steering_unwind=15.0,
                ),
            ),
            target_exits=(
                corner_exit(
                    exit_number=2,
                    apex=0.31,
                    exit_progress=0.40,
                    throttle_progress=0.35,
                    time_to_throttle=1.4,
                    exit_speed=126.0,
                    throttle_at_exit=0.75,
                    steering_at_exit=9.0,
                    steering_unwind=11.0,
                ),
            ),
            trace_comparison=(
                trace_comparison()
            ),
        )
    )

    report = (
        AssettoCorsaCornerExitDiagnosticService()
        .analyze(
            comparison
        )
    )

    assert (
        report.primary_diagnostic
        is not None
    )

    assert (
        report.primary_diagnostic.severity
        == CornerExitDiagnosticSeverity.MEDIUM
    )


def test_no_time_loss_means_no_diagnosis() -> None:
    comparison = LapTraceComparison(
        reference_lap_number=2,
        target_lap_number=5,
        start_progress=0.0,
        end_progress=1.0,
        points=(
            point(
                progress=0.30,
                time_delta=0.30,
            ),
            point(
                progress=0.38,
                time_delta=0.30,
            ),
        ),
        final_time_delta_seconds=0.30,
        average_speed_delta_kmh=0.0,
        largest_speed_loss_progress=None,
        largest_speed_gain_progress=None,
    )

    result = (
        AssettoCorsaCornerExitComparisonService()
        .compare(
            reference_exits=(
                corner_exit(
                    exit_number=1,
                    apex=0.30,
                    exit_progress=0.38,
                    throttle_progress=0.32,
                    time_to_throttle=1.0,
                    exit_speed=132.0,
                    throttle_at_exit=0.9,
                    steering_at_exit=5.0,
                    steering_unwind=15.0,
                ),
            ),
            target_exits=(
                corner_exit(
                    exit_number=2,
                    apex=0.31,
                    exit_progress=0.40,
                    throttle_progress=0.36,
                    time_to_throttle=1.5,
                    exit_speed=120.0,
                    throttle_at_exit=0.6,
                    steering_at_exit=10.0,
                    steering_unwind=10.0,
                ),
            ),
            trace_comparison=comparison,
        )
    )

    report = (
        AssettoCorsaCornerExitDiagnosticService()
        .analyze(
            result
        )
    )

    assert (
        report.diagnostic_count
        == 0
    )