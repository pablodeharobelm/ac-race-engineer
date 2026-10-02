import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace_braking_diagnostics import (
    BrakingDiagnostic,
    BrakingDiagnosticCode,
    BrakingDiagnosticReport,
    BrakingDiagnosticSeverity,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_diagnostics import (
    CornerEntryDiagnostic,
    CornerEntryDiagnosticCode,
    CornerEntryDiagnosticReport,
    CornerEntryDiagnosticSeverity,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_diagnostics import (
    CornerExitDiagnostic,
    CornerExitDiagnosticCode,
    CornerExitDiagnosticReport,
    CornerExitDiagnosticSeverity,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    AssettoCorsaRealDrivingDiagnosticService,
    DrivingDiagnosticSource,
    DrivingPhase,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation_comparison import (
    TrackCornerSegmentDelta,
    TrackSegmentationComparisonResult,
)


def corner_delta(
    *,
    reference_corner: int,
    target_corner: int,
    start: float,
    apex: float,
    exit_progress: float,
    minimum_speed_delta: float,
    apex_speed_delta: float,
    exit_speed_delta: float,
    entry_time_change: float,
    exit_time_change: float,
) -> TrackCornerSegmentDelta:
    total_change = (
        entry_time_change
        + exit_time_change
    )

    start_time_delta = 0.10

    apex_time_delta = (
        start_time_delta
        + entry_time_change
    )

    exit_time_delta = (
        apex_time_delta
        + exit_time_change
    )

    return TrackCornerSegmentDelta(
        reference_corner_number=(
            reference_corner
        ),
        target_corner_number=(
            target_corner
        ),
        reference_braking_start_progress=(
            start
        ),
        target_braking_start_progress=(
            start
        ),
        braking_start_progress_delta=0.0,
        reference_turn_in_progress=(
            start + 0.04
        ),
        target_turn_in_progress=(
            start + 0.04
        ),
        turn_in_progress_delta=0.0,
        reference_apex_progress=(
            apex
        ),
        target_apex_progress=(
            apex
        ),
        apex_progress_delta=0.0,
        reference_throttle_application_progress=(
            apex + 0.02
        ),
        target_throttle_application_progress=(
            apex + 0.02
        ),
        throttle_application_progress_delta=0.0,
        reference_exit_progress=(
            exit_progress
        ),
        target_exit_progress=(
            exit_progress
        ),
        exit_progress_delta=0.0,
        reference_minimum_speed_kmh=100.0,
        target_minimum_speed_kmh=(
            100.0
            + minimum_speed_delta
        ),
        minimum_speed_delta_kmh=(
            minimum_speed_delta
        ),
        reference_apex_speed_kmh=100.0,
        target_apex_speed_kmh=(
            100.0
            + apex_speed_delta
        ),
        apex_speed_delta_kmh=(
            apex_speed_delta
        ),
        reference_exit_speed_kmh=130.0,
        target_exit_speed_kmh=(
            130.0
            + exit_speed_delta
        ),
        exit_speed_delta_kmh=(
            exit_speed_delta
        ),
        reference_total_duration_seconds=8.0,
        target_total_duration_seconds=(
            8.0 + total_change
        ),
        total_duration_delta_seconds=(
            total_change
        ),
        time_delta_at_start_seconds=(
            start_time_delta
        ),
        time_delta_at_apex_seconds=(
            apex_time_delta
        ),
        time_delta_at_exit_seconds=(
            exit_time_delta
        ),
        time_delta_to_apex_change_seconds=(
            entry_time_change
        ),
        time_delta_exit_change_seconds=(
            exit_time_change
        ),
        time_delta_total_change_seconds=(
            total_change
        ),
    )


def segmentation() -> TrackSegmentationComparisonResult:
    return TrackSegmentationComparisonResult(
        reference_lap_number=2,
        target_lap_number=5,
        corners=(
            corner_delta(
                reference_corner=1,
                target_corner=1,
                start=0.20,
                apex=0.30,
                exit_progress=0.38,
                minimum_speed_delta=-6.0,
                apex_speed_delta=-6.0,
                exit_speed_delta=-5.0,
                entry_time_change=0.20,
                exit_time_change=0.15,
            ),
            corner_delta(
                reference_corner=2,
                target_corner=2,
                start=0.60,
                apex=0.68,
                exit_progress=0.76,
                minimum_speed_delta=3.0,
                apex_speed_delta=3.0,
                exit_speed_delta=4.0,
                entry_time_change=-0.10,
                exit_time_change=-0.05,
            ),
        ),
        unmatched_reference_corners=(),
        unmatched_target_corners=(),
    )


def braking_report() -> BrakingDiagnosticReport:
    diagnostic = BrakingDiagnostic(
        code=(
            BrakingDiagnosticCode
            .BRAKING_TOO_EARLY
        ),
        severity=(
            BrakingDiagnosticSeverity.MEDIUM
        ),
        reference_zone_number=1,
        target_zone_number=7,
        center_progress=0.23,
        time_loss_seconds=0.35,
        summary="Target brakes earlier.",
        evidence=(),
    )

    return BrakingDiagnosticReport(
        reference_lap_number=2,
        target_lap_number=5,
        diagnostics=(
            diagnostic,
        ),
        zones_analyzed=2,
        zones_with_time_loss=1,
        total_time_loss_seconds=0.35,
    )


def entry_report() -> CornerEntryDiagnosticReport:
    diagnostic = CornerEntryDiagnostic(
        code=(
            CornerEntryDiagnosticCode
            .POOR_APEX_SPEED
        ),
        severity=(
            CornerEntryDiagnosticSeverity
            .MEDIUM
        ),
        reference_entry_number=1,
        target_entry_number=7,
        center_progress=0.29,
        time_loss_seconds=0.35,
        summary="Target has lower apex speed.",
        evidence=(),
    )

    return CornerEntryDiagnosticReport(
        reference_lap_number=2,
        target_lap_number=5,
        diagnostics=(
            diagnostic,
        ),
        entries_analyzed=2,
        entries_with_time_loss=1,
        total_time_loss_seconds=0.35,
    )


def exit_report() -> CornerExitDiagnosticReport:
    diagnostic = CornerExitDiagnostic(
        code=(
            CornerExitDiagnosticCode
            .POOR_EXIT_SPEED
        ),
        severity=(
            CornerExitDiagnosticSeverity.MEDIUM
        ),
        reference_exit_number=1,
        target_exit_number=7,
        center_progress=0.35,
        time_loss_seconds=0.35,
        summary="Target has lower exit speed.",
        evidence=(),
    )

    return CornerExitDiagnosticReport(
        reference_lap_number=2,
        target_lap_number=5,
        diagnostics=(
            diagnostic,
        ),
        exits_analyzed=2,
        exits_with_time_loss=1,
        total_time_loss_seconds=0.35,
    )


def test_combines_all_diagnostic_sources() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    first = report.corners[0]

    assert first.reference_corner_number == 1
    assert first.issue_count == 3

    assert {
        issue.source
        for issue in first.issues
    } == {
        DrivingDiagnosticSource.BRAKING,
        DrivingDiagnosticSource.CORNER_ENTRY,
        DrivingDiagnosticSource.CORNER_EXIT,
    }


def test_uses_segmentation_as_time_authority() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    first = report.corners[0]

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

    assert (
        report.total_time_lost_seconds
        == pytest.approx(
            0.35
        )
    )


def test_does_not_double_count_diagnostic_time_loss() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    first = report.corners[0]

    assert first.issue_count == 3

    assert sum(
        issue.diagnostic_time_loss_seconds
        for issue in first.issues
    ) == pytest.approx(
        1.05
    )

    assert (
        first.time_lost_seconds
        == pytest.approx(
            0.35
        )
    )


def test_identifies_entry_as_dominant_phase() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    first = report.corners[0]

    assert (
        first.dominant_phase
        == DrivingPhase.ENTRY
    )


def test_preserves_speed_deltas() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    first = report.corners[0]

    assert (
        first.minimum_speed_delta_kmh
        == pytest.approx(
            -6.0
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
            -5.0
        )
    )


def test_prioritizes_largest_corner_loss() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    assert (
        report.primary_problem_corner
        is not None
    )

    assert (
        report.primary_problem_corner
        .reference_corner_number
        == 1
    )

    assert (
        report.corners[0]
        .reference_corner_number
        == 1
    )


def test_gain_corner_is_not_problem_corner() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    second = next(
        corner
        for corner in report.corners
        if (
            corner.reference_corner_number
            == 2
        )
    )

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

    assert (
        second.dominant_phase
        == DrivingPhase.NONE
    )


def test_counts_corners_with_loss_and_issues() -> None:
    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=braking_report(),
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    assert (
        report.diagnosed_corner_count
        == 2
    )

    assert (
        report.corners_with_time_loss
        == 1
    )

    assert (
        report.corners_with_issues
        == 1
    )


def test_reports_unmatched_issue() -> None:
    rogue = BrakingDiagnostic(
        code=(
            BrakingDiagnosticCode
            .BRAKING_TOO_LATE
        ),
        severity=(
            BrakingDiagnosticSeverity.LOW
        ),
        reference_zone_number=99,
        target_zone_number=99,
        center_progress=0.95,
        time_loss_seconds=0.10,
        summary="Unmatched issue.",
        evidence=(),
    )

    base = braking_report()

    modified_braking = BrakingDiagnosticReport(
        reference_lap_number=(
            base.reference_lap_number
        ),
        target_lap_number=(
            base.target_lap_number
        ),
        diagnostics=(
            *base.diagnostics,
            rogue,
        ),
        zones_analyzed=3,
        zones_with_time_loss=2,
        total_time_loss_seconds=0.45,
    )

    report = (
        AssettoCorsaRealDrivingDiagnosticService()
        .analyze(
            segmentation=segmentation(),
            braking_report=modified_braking,
            entry_report=entry_report(),
            exit_report=exit_report(),
        )
    )

    assert (
        report.unmatched_issue_count
        == 1
    )


def test_rejects_reports_for_different_laps() -> None:
    wrong = BrakingDiagnosticReport(
        reference_lap_number=3,
        target_lap_number=5,
        diagnostics=(),
        zones_analyzed=0,
        zones_with_time_loss=0,
        total_time_loss_seconds=0.0,
    )

    service = (
        AssettoCorsaRealDrivingDiagnosticService()
    )

    with pytest.raises(
        ValueError,
        match="same laps",
    ):
        service.analyze(
            segmentation=segmentation(),
            braking_report=wrong,
            entry_report=entry_report(),
            exit_report=exit_report(),
        )


def test_rejects_invalid_progress_tolerance() -> None:
    with pytest.raises(
        ValueError,
        match="progress_tolerance",
    ):
        AssettoCorsaRealDrivingDiagnosticService(
            progress_tolerance=-0.1
        )