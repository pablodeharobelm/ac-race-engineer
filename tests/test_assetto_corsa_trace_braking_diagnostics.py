import pytest

from ac_race_engineer.telemetry.assetto_corsa.trace_braking_comparison import (
    BrakingComparisonResult,
    BrakingZoneDelta,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking_diagnostics import (
    AssettoCorsaBrakingDiagnosticService,
    BrakingDiagnosticCode,
    BrakingDiagnosticSeverity,
)


def zone_delta(
    *,
    reference_zone_number: int = 1,
    target_zone_number: int = 1,
    center_progress: float = 0.25,
    start_progress_delta: float = 0.0,
    end_progress_delta: float = 0.0,
    duration_delta_seconds: float = 0.0,
    minimum_speed_delta_kmh: float = 0.0,
    peak_brake_delta: float = 0.0,
    average_brake_delta: float = 0.0,
    time_loss_seconds: float = 0.30,
) -> BrakingZoneDelta:
    reference_start = (
        center_progress
        - 0.05
    )

    reference_end = (
        center_progress
        + 0.05
    )

    target_start = (
        reference_start
        + start_progress_delta
    )

    target_end = (
        reference_end
        + end_progress_delta
    )

    reference_duration = 3.0

    target_duration = (
        reference_duration
        + duration_delta_seconds
    )

    reference_entry_speed = 160.0
    target_entry_speed = 160.0

    reference_minimum_speed = 100.0

    target_minimum_speed = (
        reference_minimum_speed
        + minimum_speed_delta_kmh
    )

    reference_exit_speed = 110.0
    target_exit_speed = 110.0

    reference_peak_brake = 0.80

    target_peak_brake = (
        reference_peak_brake
        + peak_brake_delta
    )

    reference_average_brake = 0.50

    target_average_brake = (
        reference_average_brake
        + average_brake_delta
    )

    time_delta_start = 0.10

    time_delta_end = (
        time_delta_start
        + time_loss_seconds
    )

    return BrakingZoneDelta(
        reference_zone_number=(
            reference_zone_number
        ),
        target_zone_number=(
            target_zone_number
        ),
        reference_start_progress=(
            reference_start
        ),
        target_start_progress=(
            target_start
        ),
        start_progress_delta=(
            start_progress_delta
        ),
        reference_end_progress=(
            reference_end
        ),
        target_end_progress=(
            target_end
        ),
        end_progress_delta=(
            end_progress_delta
        ),
        reference_center_progress=(
            center_progress
        ),
        target_center_progress=(
            center_progress
        ),
        center_progress_delta=0.0,
        reference_duration_seconds=(
            reference_duration
        ),
        target_duration_seconds=(
            target_duration
        ),
        duration_delta_seconds=(
            duration_delta_seconds
        ),
        reference_entry_speed_kmh=(
            reference_entry_speed
        ),
        target_entry_speed_kmh=(
            target_entry_speed
        ),
        entry_speed_delta_kmh=0.0,
        reference_minimum_speed_kmh=(
            reference_minimum_speed
        ),
        target_minimum_speed_kmh=(
            target_minimum_speed
        ),
        minimum_speed_delta_kmh=(
            minimum_speed_delta_kmh
        ),
        reference_exit_speed_kmh=(
            reference_exit_speed
        ),
        target_exit_speed_kmh=(
            target_exit_speed
        ),
        exit_speed_delta_kmh=0.0,
        reference_peak_brake=(
            reference_peak_brake
        ),
        target_peak_brake=(
            target_peak_brake
        ),
        peak_brake_delta=(
            peak_brake_delta
        ),
        reference_average_brake=(
            reference_average_brake
        ),
        target_average_brake=(
            target_average_brake
        ),
        average_brake_delta=(
            average_brake_delta
        ),
        time_delta_at_start_seconds=(
            time_delta_start
        ),
        time_delta_at_end_seconds=(
            time_delta_end
        ),
        time_delta_change_seconds=(
            time_loss_seconds
        ),
        overlap_progress=0.08,
        overlap_ratio=0.80,
    )


def comparison(
    *zones: BrakingZoneDelta,
) -> BrakingComparisonResult:
    return BrakingComparisonResult(
        reference_lap_number=2,
        target_lap_number=5,
        zones=tuple(
            zones
        ),
        unmatched_reference_zones=(),
        unmatched_target_zones=(),
    )


def diagnostic_codes(
    report,
) -> set[
    BrakingDiagnosticCode
]:
    return {
        diagnostic.code
        for diagnostic
        in report.diagnostics
    }


def test_detects_early_braking() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.02,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .BRAKING_TOO_EARLY
        in diagnostic_codes(
            report
        )
    )


def test_detects_late_braking() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=0.02,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .BRAKING_TOO_LATE
        in diagnostic_codes(
            report
        )
    )


def test_detects_over_slowing() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                minimum_speed_delta_kmh=-5.0,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .OVER_SLOWING
        in diagnostic_codes(
            report
        )
    )


def test_detects_late_brake_release() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                end_progress_delta=0.02,
                duration_delta_seconds=0.20,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .LATE_BRAKE_RELEASE
        in diagnostic_codes(
            report
        )
    )


def test_release_delta_alone_is_not_enough() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                end_progress_delta=0.02,
                duration_delta_seconds=0.02,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .LATE_BRAKE_RELEASE
        not in diagnostic_codes(
            report
        )
    )


def test_detects_excessive_average_brake_pressure() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                average_brake_delta=0.12,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .EXCESSIVE_BRAKE_PRESSURE
        in diagnostic_codes(
            report
        )
    )


def test_detects_excessive_peak_brake_pressure() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                peak_brake_delta=0.10,
            )
        )
    )

    assert (
        BrakingDiagnosticCode
        .EXCESSIVE_BRAKE_PRESSURE
        in diagnostic_codes(
            report
        )
    )


def test_zone_can_generate_multiple_diagnostics() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.02,
                minimum_speed_delta_kmh=-6.0,
                average_brake_delta=0.12,
                time_loss_seconds=0.35,
            )
        )
    )

    codes = diagnostic_codes(
        report
    )

    assert (
        BrakingDiagnosticCode
        .BRAKING_TOO_EARLY
        in codes
    )

    assert (
        BrakingDiagnosticCode
        .OVER_SLOWING
        in codes
    )

    assert (
        BrakingDiagnosticCode
        .EXCESSIVE_BRAKE_PRESSURE
        in codes
    )

    assert (
        report.diagnostic_count
        == 3
    )


def test_does_not_diagnose_zone_without_meaningful_time_loss() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService(
            minimum_time_loss_seconds=0.05
        )
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.03,
                minimum_speed_delta_kmh=-8.0,
                time_loss_seconds=0.02,
            )
        )
    )

    assert (
        report.diagnostics
        == ()
    )


def test_medium_severity() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.02,
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
        == BrakingDiagnosticSeverity.MEDIUM
    )


def test_high_severity() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.02,
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
        == BrakingDiagnosticSeverity.HIGH
    )


def test_low_severity() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.02,
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
        == BrakingDiagnosticSeverity.LOW
    )


def test_diagnostics_are_prioritized_by_time_loss() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                reference_zone_number=1,
                target_zone_number=1,
                center_progress=0.20,
                start_progress_delta=-0.02,
                time_loss_seconds=0.10,
            ),
            zone_delta(
                reference_zone_number=2,
                target_zone_number=2,
                center_progress=0.60,
                minimum_speed_delta_kmh=-5.0,
                time_loss_seconds=0.45,
            ),
        )
    )

    assert (
        report.diagnostics[0]
        .reference_zone_number
        == 2
    )

    assert (
        report.diagnostics[0]
        .time_loss_seconds
        == pytest.approx(
            0.45
        )
    )


def test_report_counts_analyzed_zones() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                reference_zone_number=1,
                time_loss_seconds=0.30,
            ),
            zone_delta(
                reference_zone_number=2,
                time_loss_seconds=-0.10,
            ),
        )
    )

    assert (
        report.zones_analyzed
        == 2
    )

    assert (
        report.zones_with_time_loss
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
        AssettoCorsaBrakingDiagnosticService()
    )

    report = service.analyze(
        comparison(
            zone_delta(
                start_progress_delta=-0.02,
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
            BrakingDiagnosticCode
            .BRAKING_TOO_EARLY
        )
    )

    evidence = (
        diagnostic.evidence[0]
    )

    assert (
        evidence.metric
        == "braking_start_progress"
    )

    assert (
        evidence.delta_value
        == pytest.approx(
            -0.02
        )
    )

    assert (
        evidence.unit
        == "normalized_progress"
    )


def test_empty_comparison_returns_empty_report() -> None:
    service = (
        AssettoCorsaBrakingDiagnosticService()
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
        report.zones_analyzed
        == 0
    )


def test_rejects_invalid_time_loss_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_time_loss_seconds",
    ):
        AssettoCorsaBrakingDiagnosticService(
            minimum_time_loss_seconds=-0.1
        )


def test_rejects_invalid_braking_point_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="braking_point_threshold",
    ):
        AssettoCorsaBrakingDiagnosticService(
            braking_point_threshold=0.0
        )


def test_rejects_invalid_severity_thresholds() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "high_severity_time_loss_seconds"
        ),
    ):
        AssettoCorsaBrakingDiagnosticService(
            medium_severity_time_loss_seconds=0.30,
            high_severity_time_loss_seconds=0.20,
        )