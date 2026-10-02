import pytest

from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    CornerDrivingDiagnosis,
    DrivingDiagnosticSource,
    DrivingIssue,
    DrivingPhase,
    RealDrivingDiagnosisReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    AssettoCorsaDrivingRecommendationService,
    DrivingRecommendationType,
)


def issue(
    *,
    source: DrivingDiagnosticSource,
    code: str,
    severity: str = "MEDIUM",
    progress: float = 0.30,
    time_loss: float = 0.30,
) -> DrivingIssue:
    return DrivingIssue(
        source=source,
        code=code,
        severity=severity,
        summary=(
            f"Diagnostic summary for {code}"
        ),
        center_progress=progress,
        diagnostic_time_loss_seconds=(
            time_loss
        ),
    )


def corner(
    *,
    number: int = 1,
    time_loss: float = 0.35,
    issues: tuple[
        DrivingIssue,
        ...,
    ] = (),
) -> CornerDrivingDiagnosis:
    return CornerDrivingDiagnosis(
        reference_corner_number=number,
        target_corner_number=number,
        start_progress=0.20,
        apex_progress=0.30,
        exit_progress=0.38,
        time_lost_seconds=time_loss,
        time_gained_seconds=0.0,
        entry_time_loss_seconds=0.20,
        exit_time_loss_seconds=0.15,
        dominant_phase=DrivingPhase.ENTRY,
        minimum_speed_delta_kmh=-6.0,
        apex_speed_delta_kmh=-5.0,
        exit_speed_delta_kmh=-4.0,
        issues=issues,
    )


def diagnosis(
    *corners: CornerDrivingDiagnosis,
) -> RealDrivingDiagnosisReport:
    return RealDrivingDiagnosisReport(
        reference_lap_number=2,
        target_lap_number=5,
        corners=tuple(
            corners
        ),
        unmatched_issue_count=0,
        total_time_lost_seconds=sum(
            item.time_lost_seconds
            for item in corners
        ),
        total_time_gained_seconds=0.0,
    )


def test_generates_braking_point_recommendation() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .BRAKING
                            ),
                            code=(
                                "BRAKING_TOO_EARLY"
                            ),
                        ),
                    )
                )
            )
        )
    )

    assert (
        report.recommendation_count
        == 1
    )

    recommendation = (
        report.recommendations[0]
    )

    assert (
        recommendation.recommendation_type
        == (
            DrivingRecommendationType
            .BRAKING_POINT
        )
    )

    assert (
        recommendation.phase
        == DrivingPhase.ENTRY
    )

    assert (
        recommendation.diagnostic_code
        == "BRAKING_TOO_EARLY"
    )


def test_generates_entry_recommendation() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .CORNER_ENTRY
                            ),
                            code=(
                                "POOR_APEX_SPEED"
                            ),
                        ),
                    )
                )
            )
        )
    )

    recommendation = (
        report.recommendations[0]
    )

    assert (
        recommendation.recommendation_type
        == (
            DrivingRecommendationType
            .APEX_SPEED
        )
    )

    assert (
        recommendation.phase
        == DrivingPhase.ENTRY
    )


def test_generates_exit_recommendation() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .CORNER_EXIT
                            ),
                            code=(
                                "LATE_THROTTLE_APPLICATION"
                            ),
                        ),
                    )
                )
            )
        )
    )

    recommendation = (
        report.recommendations[0]
    )

    assert (
        recommendation.recommendation_type
        == (
            DrivingRecommendationType
            .THROTTLE_APPLICATION
        )
    )

    assert (
        recommendation.phase
        == DrivingPhase.EXIT
    )


@pytest.mark.parametrize(
    (
        "source",
        "code",
        "expected_type",
    ),
    (
        (
            DrivingDiagnosticSource.BRAKING,
            "BRAKING_TOO_EARLY",
            DrivingRecommendationType.BRAKING_POINT,
        ),
        (
            DrivingDiagnosticSource.BRAKING,
            "BRAKING_TOO_LATE",
            DrivingRecommendationType.BRAKING_POINT,
        ),
        (
            DrivingDiagnosticSource.BRAKING,
            "OVER_SLOWING",
            DrivingRecommendationType.MINIMUM_SPEED,
        ),
        (
            DrivingDiagnosticSource.BRAKING,
            "LATE_BRAKE_RELEASE",
            DrivingRecommendationType.BRAKE_RELEASE,
        ),
        (
            DrivingDiagnosticSource.BRAKING,
            "EXCESSIVE_BRAKE_PRESSURE",
            DrivingRecommendationType.BRAKE_PRESSURE,
        ),
        (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "EARLY_TURN_IN",
            DrivingRecommendationType.TURN_IN,
        ),
        (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "LATE_TURN_IN",
            DrivingRecommendationType.TURN_IN,
        ),
        (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "ENTRY_OVER_SLOWING",
            DrivingRecommendationType.MINIMUM_SPEED,
        ),
        (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "EXCESSIVE_TRAIL_BRAKING",
            DrivingRecommendationType.TRAIL_BRAKING,
        ),
        (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "EXCESSIVE_STEERING",
            DrivingRecommendationType.STEERING_INPUT,
        ),
        (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "POOR_APEX_SPEED",
            DrivingRecommendationType.APEX_SPEED,
        ),
        (
            DrivingDiagnosticSource.CORNER_EXIT,
            "LATE_THROTTLE_APPLICATION",
            DrivingRecommendationType.THROTTLE_APPLICATION,
        ),
        (
            DrivingDiagnosticSource.CORNER_EXIT,
            "POOR_EXIT_SPEED",
            DrivingRecommendationType.EXIT_SPEED,
        ),
        (
            DrivingDiagnosticSource.CORNER_EXIT,
            "LOW_EXIT_THROTTLE",
            DrivingRecommendationType.THROTTLE_APPLICATION,
        ),
        (
            DrivingDiagnosticSource.CORNER_EXIT,
            "SLOW_STEERING_UNWIND",
            DrivingRecommendationType.STEERING_UNWIND,
        ),
    ),
)
def test_maps_supported_diagnostics(
    source: DrivingDiagnosticSource,
    code: str,
    expected_type: DrivingRecommendationType,
) -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=source,
                            code=code,
                        ),
                    )
                )
            )
        )
    )

    assert (
        report.recommendation_count
        == 1
    )

    assert (
        report.recommendations[0]
        .recommendation_type
        == expected_type
    )


@pytest.mark.parametrize(
    (
        "severity",
        "expected_priority",
    ),
    (
        (
            "LOW",
            RecommendationPriority.LOW,
        ),
        (
            "MEDIUM",
            RecommendationPriority.MEDIUM,
        ),
        (
            "HIGH",
            RecommendationPriority.HIGH,
        ),
    ),
)
def test_maps_severity_to_priority(
    severity: str,
    expected_priority: RecommendationPriority,
) -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .BRAKING
                            ),
                            code="OVER_SLOWING",
                            severity=severity,
                        ),
                    )
                )
            )
        )
    )

    assert (
        report.recommendations[0].priority
        == expected_priority
    )


def test_preserves_corner_evidence() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    number=3,
                    time_loss=0.42,
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .CORNER_EXIT
                            ),
                            code="POOR_EXIT_SPEED",
                            time_loss=0.42,
                        ),
                    ),
                )
            )
        )
    )

    recommendation = (
        report.recommendations[0]
    )

    assert (
        recommendation.corner_number
        == 3
    )

    assert (
        recommendation.corner_time_loss_seconds
        == pytest.approx(
            0.42
        )
    )

    assert (
        recommendation
        .diagnostic_time_loss_seconds
        == pytest.approx(
            0.42
        )
    )

    assert (
        recommendation.minimum_speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )

    assert (
        recommendation.apex_speed_delta_kmh
        == pytest.approx(
            -5.0
        )
    )

    assert (
        recommendation.exit_speed_delta_kmh
        == pytest.approx(
            -4.0
        )
    )


def test_generates_multiple_recommendations_for_corner() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .BRAKING
                            ),
                            code="OVER_SLOWING",
                        ),
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .CORNER_ENTRY
                            ),
                            code="POOR_APEX_SPEED",
                        ),
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .CORNER_EXIT
                            ),
                            code="POOR_EXIT_SPEED",
                        ),
                    )
                )
            )
        )
    )

    assert (
        report.recommendation_count
        == 3
    )

    assert (
        report.corners_with_recommendations
        == 1
    )

    assert len(
        report.for_corner(
            1
        )
    ) == 3


def test_ignores_corner_below_time_loss_threshold() -> None:
    service = (
        AssettoCorsaDrivingRecommendationService(
            minimum_corner_time_loss_seconds=0.05
        )
    )

    report = service.generate(
        diagnosis(
            corner(
                time_loss=0.02,
                issues=(
                    issue(
                        source=(
                            DrivingDiagnosticSource
                            .BRAKING
                        ),
                        code="OVER_SLOWING",
                    ),
                ),
            )
        )
    )

    assert (
        report.recommendation_count
        == 0
    )


def test_reports_unknown_diagnostic() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner(
                    issues=(
                        issue(
                            source=(
                                DrivingDiagnosticSource
                                .BRAKING
                            ),
                            code=(
                                "FUTURE_DIAGNOSTIC"
                            ),
                        ),
                    )
                )
            )
        )
    )

    assert (
        report.recommendation_count
        == 0
    )

    assert (
        report.unmapped_issue_count
        == 1
    )


def test_gaining_corner_does_not_generate_recommendation() -> None:
    gaining_corner = CornerDrivingDiagnosis(
        reference_corner_number=2,
        target_corner_number=2,
        start_progress=0.60,
        apex_progress=0.68,
        exit_progress=0.76,
        time_lost_seconds=0.0,
        time_gained_seconds=0.15,
        entry_time_loss_seconds=0.0,
        exit_time_loss_seconds=0.0,
        dominant_phase=DrivingPhase.NONE,
        minimum_speed_delta_kmh=3.0,
        apex_speed_delta_kmh=3.0,
        exit_speed_delta_kmh=4.0,
        issues=(
            issue(
                source=(
                    DrivingDiagnosticSource
                    .CORNER_EXIT
                ),
                code="POOR_EXIT_SPEED",
            ),
        ),
    )

    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                gaining_corner
            )
        )
    )

    assert (
        report.recommendation_count
        == 0
    )


def test_report_keeps_lap_identity() -> None:
    report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis(
                corner()
            )
        )
    )

    assert (
        report.reference_lap_number
        == 2
    )

    assert (
        report.target_lap_number
        == 5
    )

    assert (
        report.corners_analyzed
        == 1
    )


def test_rejects_negative_time_loss_threshold() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "minimum_corner_time_loss_seconds"
        ),
    ):
        AssettoCorsaDrivingRecommendationService(
            minimum_corner_time_loss_seconds=-0.1
        )