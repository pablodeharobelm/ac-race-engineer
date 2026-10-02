import pytest

from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    AssettoCorsaCoachingStrategyService,
    CoachingFocusLevel,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    DrivingDiagnosticSource,
    DrivingPhase,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    DrivingRecommendation,
    DrivingRecommendationReport,
    DrivingRecommendationType,
)


def recommendation(
    *,
    corner: int,
    recommendation_type: DrivingRecommendationType,
    priority: RecommendationPriority,
    corner_loss: float,
    diagnostic_loss: float,
    phase: DrivingPhase = DrivingPhase.ENTRY,
) -> DrivingRecommendation:
    return DrivingRecommendation(
        recommendation_type=(
            recommendation_type
        ),
        priority=priority,
        corner_number=corner,
        phase=phase,
        source=(
            DrivingDiagnosticSource.BRAKING
        ),
        diagnostic_code=(
            recommendation_type.value
        ),
        title=(
            f"Recommendation "
            f"{recommendation_type.value}"
        ),
        instruction="Test instruction.",
        rationale="Test rationale.",
        corner_time_loss_seconds=(
            corner_loss
        ),
        diagnostic_time_loss_seconds=(
            diagnostic_loss
        ),
        minimum_speed_delta_kmh=-5.0,
        apex_speed_delta_kmh=-4.0,
        exit_speed_delta_kmh=-3.0,
    )


def report(
    *recommendations: DrivingRecommendation,
) -> DrivingRecommendationReport:
    return DrivingRecommendationReport(
        reference_lap_number=2,
        target_lap_number=5,
        recommendations=tuple(
            recommendations
        ),
        corners_analyzed=3,
        corners_with_recommendations=len(
            {
                item.corner_number
                for item in recommendations
            }
        ),
        unmapped_issue_count=0,
        total_time_loss_seconds=sum(
            {
                (
                    item.corner_number,
                    item.corner_time_loss_seconds,
                )
                for item in recommendations
            },
            (),
        )
        if False
        else 0.70,
    )


def test_selects_highest_impact_recommendation() -> None:
    input_report = report(
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .BRAKING_POINT
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.40,
            diagnostic_loss=0.40,
        ),
        recommendation(
            corner=2,
            recommendation_type=(
                DrivingRecommendationType
                .EXIT_SPEED
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            corner_loss=0.20,
            diagnostic_loss=0.20,
            phase=DrivingPhase.EXIT,
        ),
    )

    plan = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            input_report
        )
    )

    assert (
        plan.primary_focus
        is not None
    )

    assert (
        plan.primary_focus.corner_number
        == 1
    )

    assert (
        plan.primary_focus.focus_level
        == CoachingFocusLevel.PRIMARY
    )


def test_limits_total_focuses() -> None:
    input_report = report(
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .BRAKING_POINT
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.40,
            diagnostic_loss=0.40,
        ),
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .APEX_SPEED
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            corner_loss=0.40,
            diagnostic_loss=0.30,
        ),
        recommendation(
            corner=2,
            recommendation_type=(
                DrivingRecommendationType
                .EXIT_SPEED
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            corner_loss=0.20,
            diagnostic_loss=0.20,
            phase=DrivingPhase.EXIT,
        ),
        recommendation(
            corner=3,
            recommendation_type=(
                DrivingRecommendationType
                .TURN_IN
            ),
            priority=(
                RecommendationPriority.LOW
            ),
            corner_loss=0.10,
            diagnostic_loss=0.10,
        ),
    )

    plan = (
        AssettoCorsaCoachingStrategyService(
            maximum_focuses=3
        )
        .build_plan(
            input_report
        )
    )

    assert (
        plan.recommendations_selected
        == 3
    )

    assert len(
        plan.focuses
    ) == 3


def test_limits_focuses_per_corner() -> None:
    input_report = report(
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .BRAKING_POINT
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.50,
            diagnostic_loss=0.50,
        ),
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .APEX_SPEED
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.50,
            diagnostic_loss=0.40,
        ),
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .STEERING_INPUT
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.50,
            diagnostic_loss=0.30,
        ),
        recommendation(
            corner=2,
            recommendation_type=(
                DrivingRecommendationType
                .EXIT_SPEED
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            corner_loss=0.20,
            diagnostic_loss=0.20,
            phase=DrivingPhase.EXIT,
        ),
    )

    plan = (
        AssettoCorsaCoachingStrategyService(
            maximum_focuses=4,
            maximum_focuses_per_corner=2,
        )
        .build_plan(
            input_report
        )
    )

    corner_one = [
        focus
        for focus in plan.focuses
        if focus.corner_number == 1
    ]

    assert len(
        corner_one
    ) == 2

    assert (
        plan.affected_corner_count
        == 2
    )


def test_deduplicates_same_recommendation_type() -> None:
    input_report = report(
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .THROTTLE_APPLICATION
            ),
            priority=(
                RecommendationPriority.LOW
            ),
            corner_loss=0.30,
            diagnostic_loss=0.15,
            phase=DrivingPhase.EXIT,
        ),
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .THROTTLE_APPLICATION
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.30,
            diagnostic_loss=0.30,
            phase=DrivingPhase.EXIT,
        ),
    )

    plan = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            input_report
        )
    )

    assert (
        plan.recommendations_selected
        == 1
    )

    assert (
        plan.focuses[0]
        .recommendation.priority
        == RecommendationPriority.HIGH
    )


def test_assigns_focus_levels() -> None:
    input_report = report(
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .BRAKING_POINT
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.40,
            diagnostic_loss=0.40,
        ),
        recommendation(
            corner=2,
            recommendation_type=(
                DrivingRecommendationType
                .APEX_SPEED
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            corner_loss=0.25,
            diagnostic_loss=0.25,
        ),
        recommendation(
            corner=3,
            recommendation_type=(
                DrivingRecommendationType
                .EXIT_SPEED
            ),
            priority=(
                RecommendationPriority.LOW
            ),
            corner_loss=0.10,
            diagnostic_loss=0.10,
            phase=DrivingPhase.EXIT,
        ),
    )

    plan = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            input_report
        )
    )

    assert (
        plan.focuses[0].focus_level
        == CoachingFocusLevel.PRIMARY
    )

    assert (
        plan.focuses[1].focus_level
        == CoachingFocusLevel.SECONDARY
    )

    assert (
        plan.focuses[2].focus_level
        == CoachingFocusLevel.OPTIONAL
    )


def test_reports_suppressed_recommendations() -> None:
    input_report = report(
        recommendation(
            corner=1,
            recommendation_type=(
                DrivingRecommendationType
                .BRAKING_POINT
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            corner_loss=0.40,
            diagnostic_loss=0.40,
        ),
        recommendation(
            corner=2,
            recommendation_type=(
                DrivingRecommendationType
                .APEX_SPEED
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            corner_loss=0.25,
            diagnostic_loss=0.25,
        ),
        recommendation(
            corner=3,
            recommendation_type=(
                DrivingRecommendationType
                .EXIT_SPEED
            ),
            priority=(
                RecommendationPriority.LOW
            ),
            corner_loss=0.15,
            diagnostic_loss=0.15,
            phase=DrivingPhase.EXIT,
        ),
    )

    plan = (
        AssettoCorsaCoachingStrategyService(
            maximum_focuses=2
        )
        .build_plan(
            input_report
        )
    )

    assert (
        plan.recommendations_considered
        == 3
    )

    assert (
        plan.recommendations_selected
        == 2
    )

    assert (
        plan.recommendations_suppressed
        == 1
    )


def test_empty_report_generates_empty_plan() -> None:
    input_report = report()

    plan = (
        AssettoCorsaCoachingStrategyService()
        .build_plan(
            input_report
        )
    )

    assert (
        plan.primary_focus
        is None
    )

    assert (
        plan.recommendations_selected
        == 0
    )

    assert (
        plan.affected_corner_count
        == 0
    )


@pytest.mark.parametrize(
    (
        "maximum_focuses",
        "maximum_per_corner",
    ),
    (
        (
            0,
            1,
        ),
        (
            3,
            0,
        ),
    ),
)
def test_rejects_invalid_limits(
    maximum_focuses: int,
    maximum_per_corner: int,
) -> None:
    with pytest.raises(
        ValueError
    ):
        AssettoCorsaCoachingStrategyService(
            maximum_focuses=(
                maximum_focuses
            ),
            maximum_focuses_per_corner=(
                maximum_per_corner
            ),
        )