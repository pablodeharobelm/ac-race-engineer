import pytest

from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    AssettoCorsaCoachingStrategyService,
    CoachingFocusLevel,
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
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
    AssettoCorsaRaceEngineerReportService,
    RaceEngineerTrend,
)


def driving_issue(
    *,
    source: DrivingDiagnosticSource,
    code: str,
    severity: str,
    progress: float,
    time_loss: float,
) -> DrivingIssue:
    return DrivingIssue(
        source=source,
        code=code,
        severity=severity,
        summary=code,
        center_progress=progress,
        diagnostic_time_loss_seconds=(
            time_loss
        ),
    )


def losing_corner() -> CornerDrivingDiagnosis:
    return CornerDrivingDiagnosis(
        reference_corner_number=1,
        target_corner_number=1,
        start_progress=0.20,
        apex_progress=0.30,
        exit_progress=0.38,
        time_lost_seconds=0.35,
        time_gained_seconds=0.0,
        entry_time_loss_seconds=0.20,
        exit_time_loss_seconds=0.15,
        dominant_phase=DrivingPhase.ENTRY,
        minimum_speed_delta_kmh=-6.0,
        apex_speed_delta_kmh=-5.0,
        exit_speed_delta_kmh=-4.0,
        issues=(
            driving_issue(
                source=(
                    DrivingDiagnosticSource.BRAKING
                ),
                code="BRAKING_TOO_EARLY",
                severity="HIGH",
                progress=0.22,
                time_loss=0.35,
            ),
            driving_issue(
                source=(
                    DrivingDiagnosticSource
                    .CORNER_ENTRY
                ),
                code="POOR_APEX_SPEED",
                severity="MEDIUM",
                progress=0.30,
                time_loss=0.35,
            ),
            driving_issue(
                source=(
                    DrivingDiagnosticSource
                    .CORNER_EXIT
                ),
                code="POOR_EXIT_SPEED",
                severity="MEDIUM",
                progress=0.36,
                time_loss=0.35,
            ),
        ),
    )


def gaining_corner() -> CornerDrivingDiagnosis:
    return CornerDrivingDiagnosis(
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
        minimum_speed_delta_kmh=2.0,
        apex_speed_delta_kmh=3.0,
        exit_speed_delta_kmh=4.0,
        issues=(),
    )


def diagnosis() -> RealDrivingDiagnosisReport:
    return RealDrivingDiagnosisReport(
        reference_lap_number=2,
        target_lap_number=5,
        corners=(
            losing_corner(),
            gaining_corner(),
        ),
        unmatched_issue_count=0,
        total_time_lost_seconds=0.35,
        total_time_gained_seconds=0.15,
    )


def build_inputs():
    diagnosis_report = diagnosis()

    recommendation_report = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis_report
        )
    )

    coaching_plan = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            recommendation_report
        )
    )

    return (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    )


def test_builds_race_engineer_report() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
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
        == 2
    )


def test_calculates_net_time_delta() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
        )
    )

    assert (
        report.total_time_lost_seconds
        == pytest.approx(
            0.35
        )
    )

    assert (
        report.total_time_gained_seconds
        == pytest.approx(
            0.15
        )
    )

    assert (
        report.net_time_delta_seconds
        == pytest.approx(
            0.20
        )
    )

    assert (
        report.trend
        == RaceEngineerTrend.LOSING_TIME
    )


def test_identifies_primary_problem_corner() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
        )
    )

    assert (
        report.primary_problem_corner
        == 1
    )


def test_builds_corner_summaries() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
        )
    )

    assert len(
        report.corners
    ) == 2

    first = report.corners[0]

    assert (
        first.corner_number
        == 1
    )

    assert (
        first.time_lost_seconds
        == pytest.approx(
            0.35
        )
    )

    assert (
        first.minimum_speed_delta_kmh
        == pytest.approx(
            -6.0
        )
    )

    assert (
        first.apex_speed_delta_kmh
        == pytest.approx(
            -5.0
        )
    )

    assert (
        first.exit_speed_delta_kmh
        == pytest.approx(
            -4.0
        )
    )

    assert (
        first.issue_count
        == 3
    )


def test_builds_prioritized_focuses() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
        )
    )

    assert (
        report.has_actionable_focus
        is True
    )

    assert (
        report.primary_focus
        is not None
    )

    assert (
        report.primary_focus.rank
        == 1
    )

    assert (
        report.primary_focus.focus_level
        == CoachingFocusLevel.PRIMARY
    )

    assert (
        report.primary_focus.corner_number
        == 1
    )


def test_preserves_recommendation_priority() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
        )
    )

    assert (
        report.primary_focus
        is not None
    )

    assert (
        report.primary_focus.priority
        == RecommendationPriority.HIGH
    )


def test_reports_recommendation_counts() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=coaching_plan,
        )
    )

    assert (
        report.recommendations_generated
        == recommendation_report
        .recommendation_count
    )

    assert (
        report.recommendations_selected
        == coaching_plan
        .recommendations_selected
    )

    assert (
        report.recommendations_suppressed
        == coaching_plan
        .recommendations_suppressed
    )


def test_detects_gaining_time_trend() -> None:
    diagnosis_report = (
        RealDrivingDiagnosisReport(
            reference_lap_number=2,
            target_lap_number=5,
            corners=(
                gaining_corner(),
            ),
            unmatched_issue_count=0,
            total_time_lost_seconds=0.0,
            total_time_gained_seconds=0.15,
        )
    )

    recommendations = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis_report
        )
    )

    coaching = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            recommendations
        )
    )

    report = (
        AssettoCorsaRaceEngineerReportService()
        .build(
            diagnosis=diagnosis_report,
            recommendations=recommendations,
            coaching_plan=coaching,
        )
    )

    assert (
        report.trend
        == RaceEngineerTrend.GAINING_TIME
    )

    assert (
        report.net_time_delta_seconds
        == pytest.approx(
            -0.15
        )
    )


def test_detects_neutral_trend() -> None:
    diagnosis_report = (
        RealDrivingDiagnosisReport(
            reference_lap_number=2,
            target_lap_number=5,
            corners=(),
            unmatched_issue_count=0,
            total_time_lost_seconds=0.20,
            total_time_gained_seconds=0.195,
        )
    )

    recommendations = (
        AssettoCorsaDrivingRecommendationService()
        .generate(
            diagnosis_report
        )
    )

    coaching = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            recommendations
        )
    )

    report = (
        AssettoCorsaRaceEngineerReportService(
            neutral_tolerance_seconds=0.01
        )
        .build(
            diagnosis=diagnosis_report,
            recommendations=recommendations,
            coaching_plan=coaching,
        )
    )

    assert (
        report.trend
        == RaceEngineerTrend.NEUTRAL
    )


def test_rejects_mismatched_recommendation_laps() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    wrong_recommendations = (
        recommendation_report.__class__(
            reference_lap_number=3,
            target_lap_number=5,
            recommendations=(
                recommendation_report
                .recommendations
            ),
            corners_analyzed=(
                recommendation_report
                .corners_analyzed
            ),
            corners_with_recommendations=(
                recommendation_report
                .corners_with_recommendations
            ),
            unmapped_issue_count=(
                recommendation_report
                .unmapped_issue_count
            ),
            total_time_loss_seconds=(
                recommendation_report
                .total_time_loss_seconds
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="same laps",
    ):
        AssettoCorsaRaceEngineerReportService().build(
            diagnosis=diagnosis_report,
            recommendations=wrong_recommendations,
            coaching_plan=coaching_plan,
        )


def test_rejects_mismatched_coaching_laps() -> None:
    (
        diagnosis_report,
        recommendation_report,
        coaching_plan,
    ) = build_inputs()

    wrong_coaching = coaching_plan.__class__(
        reference_lap_number=3,
        target_lap_number=5,
        focuses=coaching_plan.focuses,
        recommendations_considered=(
            coaching_plan
            .recommendations_considered
        ),
        recommendations_selected=(
            coaching_plan
            .recommendations_selected
        ),
        recommendations_suppressed=(
            coaching_plan
            .recommendations_suppressed
        ),
        total_time_loss_seconds=(
            coaching_plan
            .total_time_loss_seconds
        ),
    )

    with pytest.raises(
        ValueError,
        match="same laps",
    ):
        AssettoCorsaRaceEngineerReportService().build(
            diagnosis=diagnosis_report,
            recommendations=(
                recommendation_report
            ),
            coaching_plan=wrong_coaching,
        )


def test_rejects_negative_neutral_tolerance() -> None:
    with pytest.raises(
        ValueError,
        match="neutral_tolerance_seconds",
    ):
        AssettoCorsaRaceEngineerReportService(
            neutral_tolerance_seconds=-0.1
        )