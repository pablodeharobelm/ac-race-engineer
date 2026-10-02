import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_comparison import (
    CornerEntryComparisonResult,
    CornerEntryDelta,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_diagnostics import (
    AssettoCorsaCornerEntryDiagnosticService,
    CornerEntryDiagnosticCode,
    CornerEntryDiagnosticSeverity,
)


def entry_delta(
    *,
    reference_entry_number: int = 1,
    target_entry_number: int = 1,
    center_progress: float = 0.30,
    turn_in_progress_delta: float = 0.0,
    apex_progress_delta: float = 0.0,
    entry_duration_delta_seconds: float = 0.0,
    brake_overlap_delta_seconds: float = 0.0,
    entry_speed_delta_kmh: float = 0.0,
    apex_speed_delta_kmh: float = 0.0,
    speed_loss_delta_kmh: float = 0.0,
    brake_at_turn_in_delta: float = 0.0,
    throttle_at_turn_in_delta: float = 0.0,
    throttle_at_apex_delta: float = 0.0,
    maximum_steering_delta_deg: float = 0.0,
    average_steering_delta_deg: float = 0.0,
    time_loss_seconds: float = 0.30,
) -> CornerEntryDelta:
    reference_turn_in = (
        center_progress
        - 0.03
    )

    reference_apex = (
        center_progress
        + 0.03
    )

    target_turn_in = (
        reference_turn_in
        + turn_in_progress_delta
    )

    target_apex = (
        reference_apex
        + apex_progress_delta
    )

    reference_duration = 5.0

    target_duration = (
        reference_duration
        + entry_duration_delta_seconds
    )

    reference_brake_overlap = 1.5

    target_brake_overlap = (
        reference_brake_overlap
        + brake_overlap_delta_seconds
    )

    reference_entry_speed = 135.0

    target_entry_speed = (
        reference_entry_speed
        + entry_speed_delta_kmh
    )

    reference_apex_speed = 100.0

    target_apex_speed = (
        reference_apex_speed
        + apex_speed_delta_kmh
    )

    reference_speed_loss = 35.0

    target_speed_loss = (
        reference_speed_loss
        + speed_loss_delta_kmh
    )

    reference_brake_at_turn_in = 0.50

    target_brake_at_turn_in = (
        reference_brake_at_turn_in
        + brake_at_turn_in_delta
    )

    reference_throttle_at_turn_in = 0.0

    target_throttle_at_turn_in = (
        reference_throttle_at_turn_in
        + throttle_at_turn_in_delta
    )

    reference_throttle_at_apex = 0.10

    target_throttle_at_apex = (
        reference_throttle_at_apex
        + throttle_at_apex_delta
    )

    reference_maximum_steering = 20.0

    target_maximum_steering = (
        reference_maximum_steering
        + maximum_steering_delta_deg
    )

    reference_average_steering = 14.0

    target_average_steering = (
        reference_average_steering
        + average_steering_delta_deg
    )

    time_delta_start = 0.10

    time_delta_end = (
        time_delta_start
        + time_loss_seconds
    )

    return CornerEntryDelta(
        reference_entry_number=(
            reference_entry_number
        ),
        target_entry_number=(
            target_entry_number
        ),
        reference_turn_in_progress=(
            reference_turn_in
        ),
        target_turn_in_progress=(
            target_turn_in
        ),
        turn_in_progress_delta=(
            turn_in_progress_delta
        ),
        reference_apex_progress=(
            reference_apex
        ),
        target_apex_progress=(
            target_apex
        ),
        apex_progress_delta=(
            apex_progress_delta
        ),
        reference_entry_duration_seconds=(
            reference_duration
        ),
        target_entry_duration_seconds=(
            target_duration
        ),
        entry_duration_delta_seconds=(
            entry_duration_delta_seconds
        ),
        reference_brake_overlap_seconds=(
            reference_brake_overlap
        ),
        target_brake_overlap_seconds=(
            target_brake_overlap
        ),
        brake_overlap_delta_seconds=(
            brake_overlap_delta_seconds
        ),
        reference_entry_speed_kmh=(
            reference_entry_speed
        ),
        target_entry_speed_kmh=(
            target_entry_speed
        ),
        entry_speed_delta_kmh=(
            entry_speed_delta_kmh
        ),
        reference_apex_speed_kmh=(
            reference_apex_speed
        ),
        target_apex_speed_kmh=(
            target_apex_speed
        ),
        apex_speed_delta_kmh=(
            apex_speed_delta_kmh
        ),
        reference_speed_loss_kmh=(
            reference_speed_loss
        ),
        target_speed_loss_kmh=(
            target_speed_loss
        ),
        speed_loss_delta_kmh=(
            speed_loss_delta_kmh
        ),
        reference_brake_at_turn_in=(
            reference_brake_at_turn_in
        ),
        target_brake_at_turn_in=(
            target_brake_at_turn_in
        ),
        brake_at_turn_in_delta=(
            brake_at_turn_in_delta
        ),
        reference_throttle_at_turn_in=(
            reference_throttle_at_turn_in
        ),
        target_throttle_at_turn_in=(
            target_throttle_at_turn_in
        ),
        throttle_at_turn_in_delta=(
            throttle_at_turn_in_delta
        ),
        reference_throttle_at_apex=(
            reference_throttle_at_apex
        ),
        target_throttle_at_apex=(
            target_throttle_at_apex
        ),
        throttle_at_apex_delta=(
            throttle_at_apex_delta
        ),
        reference_maximum_abs_steering_deg=(
            reference_maximum_steering
        ),
        target_maximum_abs_steering_deg=(
            target_maximum_steering
        ),
        maximum_abs_steering_delta_deg=(
            maximum_steering_delta_deg
        ),
        reference_average_abs_steering_deg=(
            reference_average_steering
        ),
        target_average_abs_steering_deg=(
            target_average_steering
        ),
        average_abs_steering_delta_deg=(
            average_steering_delta_deg
        ),
        time_delta_at_turn_in_seconds=(
            time_delta_start
        ),
        time_delta_at_apex_seconds=(
            time_delta_end
        ),
        time_delta_change_seconds=(
            time_loss_seconds
        ),
        overlap_progress=0.05,
        overlap_ratio=0.80,
    )


def comparison(
    *entries: CornerEntryDelta,
) -> CornerEntryComparisonResult:
    return CornerEntryComparisonResult(
        reference_lap_number=2,
        target_lap_number=5,
        entries=tuple(
            entries
        ),
        unmatched_reference_entries=(),
        unmatched_target_entries=(),
    )


def diagnostic_codes(
    report,
) -> set[
    CornerEntryDiagnosticCode
]:
    return {
        diagnostic.code
        for diagnostic
        in report.diagnostics
    }


def test_detects_early_turn_in() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=-0.02,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .EARLY_TURN_IN
        in diagnostic_codes(
            report
        )
    )


def test_detects_late_turn_in() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=0.02,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .LATE_TURN_IN
        in diagnostic_codes(
            report
        )
    )


def test_detects_entry_over_slowing() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                speed_loss_delta_kmh=5.0,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .ENTRY_OVER_SLOWING
        in diagnostic_codes(
            report
        )
    )


def test_detects_poor_apex_speed() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                apex_speed_delta_kmh=-6.0,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .POOR_APEX_SPEED
        in diagnostic_codes(
            report
        )
    )


def test_detects_excessive_trail_braking() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                brake_overlap_delta_seconds=0.30,
                brake_at_turn_in_delta=0.10,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .EXCESSIVE_TRAIL_BRAKING
        in diagnostic_codes(
            report
        )
    )


def test_overlap_alone_does_not_trigger_trail_braking() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                brake_overlap_delta_seconds=0.30,
                brake_at_turn_in_delta=0.02,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .EXCESSIVE_TRAIL_BRAKING
        not in diagnostic_codes(
            report
        )
    )


def test_detects_excessive_maximum_steering() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                maximum_steering_delta_deg=5.0,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .EXCESSIVE_STEERING
        in diagnostic_codes(
            report
        )
    )


def test_detects_excessive_average_steering() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                average_steering_delta_deg=3.0,
            )
        )
    )

    assert (
        CornerEntryDiagnosticCode
        .EXCESSIVE_STEERING
        in diagnostic_codes(
            report
        )
    )


def test_one_entry_can_generate_multiple_diagnostics() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=-0.02,
                apex_speed_delta_kmh=-6.0,
                speed_loss_delta_kmh=5.0,
                brake_overlap_delta_seconds=0.30,
                brake_at_turn_in_delta=0.10,
                maximum_steering_delta_deg=5.0,
                time_loss_seconds=0.35,
            )
        )
    )

    codes = diagnostic_codes(
        report
    )

    assert (
        CornerEntryDiagnosticCode
        .EARLY_TURN_IN
        in codes
    )

    assert (
        CornerEntryDiagnosticCode
        .ENTRY_OVER_SLOWING
        in codes
    )

    assert (
        CornerEntryDiagnosticCode
        .POOR_APEX_SPEED
        in codes
    )

    assert (
        CornerEntryDiagnosticCode
        .EXCESSIVE_TRAIL_BRAKING
        in codes
    )

    assert (
        CornerEntryDiagnosticCode
        .EXCESSIVE_STEERING
        in codes
    )

    assert (
        report.diagnostic_count
        == 5
    )


def test_does_not_diagnose_without_meaningful_time_loss() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService(
            minimum_time_loss_seconds=0.05
        )
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=-0.03,
                apex_speed_delta_kmh=-10.0,
                time_loss_seconds=0.02,
            )
        )
    )

    assert (
        report.diagnostics
        == ()
    )


def test_low_severity() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=-0.02,
                time_loss_seconds=0.10,
            )
        )
    )

    diagnostic = (
        report.primary_diagnostic
    )

    assert diagnostic is not None

    assert (
        diagnostic.severity
        == CornerEntryDiagnosticSeverity.LOW
    )


def test_medium_severity() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=-0.02,
                time_loss_seconds=0.25,
            )
        )
    )

    diagnostic = (
        report.primary_diagnostic
    )

    assert diagnostic is not None

    assert (
        diagnostic.severity
        == CornerEntryDiagnosticSeverity.MEDIUM
    )


def test_high_severity() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                turn_in_progress_delta=-0.02,
                time_loss_seconds=0.50,
            )
        )
    )

    diagnostic = (
        report.primary_diagnostic
    )

    assert diagnostic is not None

    assert (
        diagnostic.severity
        == CornerEntryDiagnosticSeverity.HIGH
    )


def test_prioritizes_largest_time_loss() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                reference_entry_number=1,
                target_entry_number=1,
                center_progress=0.25,
                turn_in_progress_delta=-0.02,
                time_loss_seconds=0.10,
            ),
            entry_delta(
                reference_entry_number=2,
                target_entry_number=2,
                center_progress=0.65,
                apex_speed_delta_kmh=-5.0,
                time_loss_seconds=0.45,
            ),
        )
    )

    assert (
        report.diagnostics[0]
        .reference_entry_number
        == 2
    )

    assert (
        report.diagnostics[0]
        .time_loss_seconds
        == pytest.approx(
            0.45
        )
    )


def test_report_counts_time_losing_entries() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                reference_entry_number=1,
                turn_in_progress_delta=-0.02,
                time_loss_seconds=0.30,
            ),
            entry_delta(
                reference_entry_number=2,
                time_loss_seconds=-0.10,
            ),
        )
    )

    assert (
        report.entries_analyzed
        == 2
    )

    assert (
        report.entries_with_time_loss
        == 1
    )

    assert (
        report.total_time_loss_seconds
        == pytest.approx(
            0.30
        )
    )


def test_evidence_contains_measured_values() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison(
            entry_delta(
                apex_speed_delta_kmh=-6.0,
                time_loss_seconds=0.30,
            )
        )
    )

    diagnostic = (
        report.primary_diagnostic
    )

    assert diagnostic is not None

    assert (
        diagnostic.code
        == (
            CornerEntryDiagnosticCode
            .POOR_APEX_SPEED
        )
    )

    evidence = (
        diagnostic.evidence[0]
    )

    assert (
        evidence.metric
        == "apex_speed"
    )

    assert (
        evidence.delta_value
        == pytest.approx(
            -6.0
        )
    )

    assert (
        evidence.unit
        == "km/h"
    )


def test_empty_comparison_returns_empty_report() -> None:
    service = (
        AssettoCorsaCornerEntryDiagnosticService()
    )

    report = service.analyze(
        comparison()
    )

    assert (
        report.diagnostic_count
        == 0
    )

    assert (
        report.primary_diagnostic
        is None
    )

    assert (
        report.entries_analyzed
        == 0
    )


def test_rejects_invalid_time_loss_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_time_loss_seconds",
    ):
        AssettoCorsaCornerEntryDiagnosticService(
            minimum_time_loss_seconds=-0.1
        )


def test_rejects_invalid_turn_in_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="turn_in_progress_threshold",
    ):
        AssettoCorsaCornerEntryDiagnosticService(
            turn_in_progress_threshold=0.0
        )


def test_rejects_invalid_apex_speed_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_apex_speed_loss_kmh",
    ):
        AssettoCorsaCornerEntryDiagnosticService(
            minimum_apex_speed_loss_kmh=0.0
        )


def test_rejects_invalid_severity_thresholds() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "high_severity_time_loss_seconds"
        ),
    ):
        AssettoCorsaCornerEntryDiagnosticService(
            medium_severity_time_loss_seconds=0.30,
            high_severity_time_loss_seconds=0.20,
        )