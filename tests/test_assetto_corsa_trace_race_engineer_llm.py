import pytest

from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    CoachingFocusLevel,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    DrivingPhase,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    DrivingRecommendationType,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_llm import (
    AssettoCorsaRaceEngineerExplanationService,
    AssettoCorsaRaceEngineerPromptBuilder,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
    RaceEngineerCornerSummary,
    RaceEngineerFocusSummary,
    RaceEngineerReport,
    RaceEngineerTrend,
)


class FakeLLMClient:
    def __init__(
        self,
        response: str = (
            "La curva 1 es el principal punto "
            "de mejora."
        ),
    ) -> None:
        self.response = response

        self.system_prompt: str | None = None
        self.user_prompt: str | None = None

        self.call_count = 0

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.call_count += 1

        self.system_prompt = (
            system_prompt
        )

        self.user_prompt = (
            user_prompt
        )

        return self.response


def report() -> RaceEngineerReport:
    return RaceEngineerReport(
        reference_lap_number=2,
        target_lap_number=5,
        trend=(
            RaceEngineerTrend.LOSING_TIME
        ),
        total_time_lost_seconds=0.35,
        total_time_gained_seconds=0.15,
        net_time_delta_seconds=0.20,
        corners_analyzed=2,
        corners_with_time_loss=1,
        corners_with_issues=1,
        recommendations_generated=3,
        recommendations_selected=2,
        recommendations_suppressed=1,
        primary_problem_corner=1,
        corners=(
            RaceEngineerCornerSummary(
                corner_number=1,
                time_lost_seconds=0.35,
                time_gained_seconds=0.0,
                entry_time_loss_seconds=0.20,
                exit_time_loss_seconds=0.15,
                dominant_phase=(
                    DrivingPhase.ENTRY
                ),
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
                issue_count=3,
            ),
            RaceEngineerCornerSummary(
                corner_number=2,
                time_lost_seconds=0.0,
                time_gained_seconds=0.15,
                entry_time_loss_seconds=0.0,
                exit_time_loss_seconds=0.0,
                dominant_phase=(
                    DrivingPhase.NONE
                ),
                minimum_speed_delta_kmh=2.0,
                apex_speed_delta_kmh=3.0,
                exit_speed_delta_kmh=4.0,
                issue_count=0,
            ),
        ),
        focuses=(
            RaceEngineerFocusSummary(
                rank=1,
                focus_level=(
                    CoachingFocusLevel.PRIMARY
                ),
                corner_number=1,
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKING_POINT
                ),
                priority=(
                    RecommendationPriority.HIGH
                ),
                phase=DrivingPhase.ENTRY,
                title="Brake slightly later",
                instruction=(
                    "Move the braking point "
                    "slightly later."
                ),
                rationale=(
                    "The target lap begins "
                    "braking earlier."
                ),
                diagnostic_code=(
                    "BRAKING_TOO_EARLY"
                ),
                corner_time_loss_seconds=0.35,
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
            ),
            RaceEngineerFocusSummary(
                rank=2,
                focus_level=(
                    CoachingFocusLevel.SECONDARY
                ),
                corner_number=1,
                recommendation_type=(
                    DrivingRecommendationType
                    .APEX_SPEED
                ),
                priority=(
                    RecommendationPriority.MEDIUM
                ),
                phase=DrivingPhase.ENTRY,
                title="Improve apex speed",
                instruction=(
                    "Preserve more speed "
                    "through the apex."
                ),
                rationale=(
                    "Apex speed is lower than "
                    "the reference."
                ),
                diagnostic_code=(
                    "POOR_APEX_SPEED"
                ),
                corner_time_loss_seconds=0.35,
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
            ),
        ),
    )


def test_builds_grounded_prompt() -> None:
    request = (
        AssettoCorsaRaceEngineerPromptBuilder()
        .build(
            report()
        )
    )

    assert (
        "Do not create new diagnoses"
        in request.system_prompt
    )

    assert (
        "Do not create new recommendations"
        in request.system_prompt
    )

    assert (
        "Reference lap: 2"
        in request.user_prompt
    )

    assert (
        "Target lap: 5"
        in request.user_prompt
    )

    assert (
        "BRAKING_TOO_EARLY"
        in request.user_prompt
    )

    assert (
        "Brake slightly later"
        in request.user_prompt
    )


def test_prompt_contains_measured_evidence() -> None:
    request = (
        AssettoCorsaRaceEngineerPromptBuilder()
        .build(
            report()
        )
    )

    assert (
        "Minimum speed delta: -6.0 km/h"
        in request.user_prompt
    )

    assert (
        "Apex speed delta: -5.0 km/h"
        in request.user_prompt
    )

    assert (
        "Exit speed delta: -4.0 km/h"
        in request.user_prompt
    )

    assert (
        "Net delta: +0.200 s"
        in request.user_prompt
    )


def test_preserves_focus_order() -> None:
    request = (
        AssettoCorsaRaceEngineerPromptBuilder()
        .build(
            report()
        )
    )

    primary_position = (
        request.user_prompt.index(
            "Focus #1"
        )
    )

    secondary_position = (
        request.user_prompt.index(
            "Focus #2"
        )
    )

    assert (
        primary_position
        < secondary_position
    )


def test_generates_explanation() -> None:
    client = FakeLLMClient(
        response=(
            "Trabaja primero la curva 1. "
            "Retrasa ligeramente la frenada."
        )
    )

    service = (
        AssettoCorsaRaceEngineerExplanationService(
            client=client
        )
    )

    explanation = service.explain(
        report()
    )

    assert (
        client.call_count
        == 1
    )

    assert (
        explanation.reference_lap_number
        == 2
    )

    assert (
        explanation.target_lap_number
        == 5
    )

    assert (
        explanation.language
        == "es"
    )

    assert (
        explanation.recommendation_count
        == 2
    )

    assert (
        "curva 1"
        in explanation.text
    )


def test_passes_prompts_to_client() -> None:
    client = FakeLLMClient()

    service = (
        AssettoCorsaRaceEngineerExplanationService(
            client=client
        )
    )

    service.explain(
        report()
    )

    assert (
        client.system_prompt
        is not None
    )

    assert (
        client.user_prompt
        is not None
    )

    assert (
        "deterministic"
        in client.system_prompt.lower()
    )

    assert (
        "APPROVED COACHING FOCUSES"
        in client.user_prompt
    )


def test_supports_requested_language() -> None:
    client = FakeLLMClient()

    explanation = (
        AssettoCorsaRaceEngineerExplanationService(
            client=client
        )
        .explain(
            report(),
            language="en",
        )
    )

    assert (
        explanation.language
        == "en"
    )

    assert (
        client.user_prompt
        is not None
    )

    assert (
        "OUTPUT LANGUAGE:\nen"
        in client.user_prompt
    )


def test_rejects_empty_language() -> None:
    with pytest.raises(
        ValueError,
        match="language",
    ):
        (
            AssettoCorsaRaceEngineerPromptBuilder()
            .build(
                report(),
                language="   ",
            )
        )


def test_rejects_empty_llm_response() -> None:
    client = FakeLLMClient(
        response="   "
    )

    service = (
        AssettoCorsaRaceEngineerExplanationService(
            client=client
        )
    )

    with pytest.raises(
        ValueError,
        match="empty explanation",
    ):
        service.explain(
            report()
        )


def test_report_without_focuses_forbids_invention() -> None:
    value = report()

    no_focus_report = RaceEngineerReport(
        reference_lap_number=(
            value.reference_lap_number
        ),
        target_lap_number=(
            value.target_lap_number
        ),
        trend=value.trend,
        total_time_lost_seconds=(
            value.total_time_lost_seconds
        ),
        total_time_gained_seconds=(
            value.total_time_gained_seconds
        ),
        net_time_delta_seconds=(
            value.net_time_delta_seconds
        ),
        corners_analyzed=(
            value.corners_analyzed
        ),
        corners_with_time_loss=(
            value.corners_with_time_loss
        ),
        corners_with_issues=(
            value.corners_with_issues
        ),
        recommendations_generated=0,
        recommendations_selected=0,
        recommendations_suppressed=0,
        primary_problem_corner=(
            value.primary_problem_corner
        ),
        corners=value.corners,
        focuses=(),
    )

    request = (
        AssettoCorsaRaceEngineerPromptBuilder()
        .build(
            no_focus_report
        )
    )

    assert (
        "Do not invent recommendations"
        in request.user_prompt
    )