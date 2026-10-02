from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    CoachingFocusLevel,
    CoachingPlan,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    DrivingPhase,
    RealDrivingDiagnosisReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    DrivingRecommendationReport,
    DrivingRecommendationType,
)


class RaceEngineerTrend(StrEnum):
    LOSING_TIME = "losing_time"
    GAINING_TIME = "gaining_time"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class RaceEngineerCornerSummary:
    corner_number: int

    time_lost_seconds: float
    time_gained_seconds: float

    entry_time_loss_seconds: float
    exit_time_loss_seconds: float

    dominant_phase: DrivingPhase

    minimum_speed_delta_kmh: float
    apex_speed_delta_kmh: float
    exit_speed_delta_kmh: float

    issue_count: int

    @property
    def net_time_delta_seconds(
        self,
    ) -> float:
        return (
            self.time_lost_seconds
            - self.time_gained_seconds
        )


@dataclass(frozen=True)
class RaceEngineerFocusSummary:
    rank: int

    focus_level: CoachingFocusLevel

    corner_number: int

    recommendation_type: DrivingRecommendationType
    priority: RecommendationPriority
    phase: DrivingPhase

    title: str
    instruction: str
    rationale: str

    diagnostic_code: str

    corner_time_loss_seconds: float

    minimum_speed_delta_kmh: float
    apex_speed_delta_kmh: float
    exit_speed_delta_kmh: float


@dataclass(frozen=True)
class RaceEngineerReport:
    reference_lap_number: int
    target_lap_number: int

    trend: RaceEngineerTrend

    total_time_lost_seconds: float
    total_time_gained_seconds: float
    net_time_delta_seconds: float

    corners_analyzed: int
    corners_with_time_loss: int
    corners_with_issues: int

    recommendations_generated: int
    recommendations_selected: int
    recommendations_suppressed: int

    primary_problem_corner: int | None

    corners: tuple[
        RaceEngineerCornerSummary,
        ...,
    ]

    focuses: tuple[
        RaceEngineerFocusSummary,
        ...,
    ]

    @property
    def primary_focus(
        self,
    ) -> RaceEngineerFocusSummary | None:
        if not self.focuses:
            return None

        return self.focuses[0]

    @property
    def has_actionable_focus(
        self,
    ) -> bool:
        return bool(
            self.focuses
        )


class AssettoCorsaRaceEngineerReportService:
    """
    Build the final deterministic race-engineer briefing.

    Inputs:

        RealDrivingDiagnosisReport
        DrivingRecommendationReport
        CoachingPlan

    Output:

        RaceEngineerReport

    This service does not create new diagnoses or
    recommendations.

    It only consolidates already validated information
    into a stable structure that can later be consumed
    by:

        - UI
        - API
        - persistence
        - LLM explanation layer
    """

    def __init__(
        self,
        *,
        neutral_tolerance_seconds: float = 0.01,
    ) -> None:
        if neutral_tolerance_seconds < 0.0:
            raise ValueError(
                "neutral_tolerance_seconds "
                "cannot be negative"
            )

        self.neutral_tolerance_seconds = (
            neutral_tolerance_seconds
        )

    @staticmethod
    def _validate_laps(
        *,
        diagnosis: RealDrivingDiagnosisReport,
        recommendations: DrivingRecommendationReport,
        coaching_plan: CoachingPlan,
    ) -> None:
        expected = (
            diagnosis.reference_lap_number,
            diagnosis.target_lap_number,
        )

        recommendation_laps = (
            recommendations.reference_lap_number,
            recommendations.target_lap_number,
        )

        coaching_laps = (
            coaching_plan.reference_lap_number,
            coaching_plan.target_lap_number,
        )

        if recommendation_laps != expected:
            raise ValueError(
                "Recommendation report must "
                "reference the same laps as "
                "the diagnosis"
            )

        if coaching_laps != expected:
            raise ValueError(
                "Coaching plan must reference "
                "the same laps as the diagnosis"
            )

    def _trend(
        self,
        net_delta_seconds: float,
    ) -> RaceEngineerTrend:
        if (
            net_delta_seconds
            > self.neutral_tolerance_seconds
        ):
            return RaceEngineerTrend.LOSING_TIME

        if (
            net_delta_seconds
            < -self.neutral_tolerance_seconds
        ):
            return RaceEngineerTrend.GAINING_TIME

        return RaceEngineerTrend.NEUTRAL

    @staticmethod
    def _corner_summaries(
        diagnosis: RealDrivingDiagnosisReport,
    ) -> tuple[
        RaceEngineerCornerSummary,
        ...,
    ]:
        summaries = [
            RaceEngineerCornerSummary(
                corner_number=(
                    corner.reference_corner_number
                ),
                time_lost_seconds=(
                    corner.time_lost_seconds
                ),
                time_gained_seconds=(
                    corner.time_gained_seconds
                ),
                entry_time_loss_seconds=(
                    corner.entry_time_loss_seconds
                ),
                exit_time_loss_seconds=(
                    corner.exit_time_loss_seconds
                ),
                dominant_phase=(
                    corner.dominant_phase
                ),
                minimum_speed_delta_kmh=(
                    corner.minimum_speed_delta_kmh
                ),
                apex_speed_delta_kmh=(
                    corner.apex_speed_delta_kmh
                ),
                exit_speed_delta_kmh=(
                    corner.exit_speed_delta_kmh
                ),
                issue_count=(
                    corner.issue_count
                ),
            )
            for corner in diagnosis.corners
        ]

        summaries.sort(
            key=lambda item: (
                item.corner_number
            )
        )

        return tuple(
            summaries
        )

    @staticmethod
    def _focus_summaries(
        coaching_plan: CoachingPlan,
    ) -> tuple[
        RaceEngineerFocusSummary,
        ...,
    ]:
        summaries = [
            RaceEngineerFocusSummary(
                rank=focus.rank,
                focus_level=focus.focus_level,
                corner_number=(
                    focus.corner_number
                ),
                recommendation_type=(
                    focus.recommendation
                    .recommendation_type
                ),
                priority=(
                    focus.recommendation.priority
                ),
                phase=(
                    focus.recommendation.phase
                ),
                title=(
                    focus.recommendation.title
                ),
                instruction=(
                    focus.recommendation.instruction
                ),
                rationale=(
                    focus.recommendation.rationale
                ),
                diagnostic_code=(
                    focus.recommendation
                    .diagnostic_code
                ),
                corner_time_loss_seconds=(
                    focus.recommendation
                    .corner_time_loss_seconds
                ),
                minimum_speed_delta_kmh=(
                    focus.recommendation
                    .minimum_speed_delta_kmh
                ),
                apex_speed_delta_kmh=(
                    focus.recommendation
                    .apex_speed_delta_kmh
                ),
                exit_speed_delta_kmh=(
                    focus.recommendation
                    .exit_speed_delta_kmh
                ),
            )
            for focus in coaching_plan.focuses
        ]

        summaries.sort(
            key=lambda item: (
                item.rank
            )
        )

        return tuple(
            summaries
        )

    def build(
        self,
        *,
        diagnosis: RealDrivingDiagnosisReport,
        recommendations: DrivingRecommendationReport,
        coaching_plan: CoachingPlan,
    ) -> RaceEngineerReport:
        self._validate_laps(
            diagnosis=diagnosis,
            recommendations=recommendations,
            coaching_plan=coaching_plan,
        )

        total_loss = (
            diagnosis.total_time_lost_seconds
        )

        total_gain = (
            diagnosis.total_time_gained_seconds
        )

        net_delta = (
            total_loss
            - total_gain
        )

        primary_problem = (
            diagnosis.primary_problem_corner
        )

        primary_problem_corner = (
            None
            if primary_problem is None
            else (
                primary_problem
                .reference_corner_number
            )
        )

        return RaceEngineerReport(
            reference_lap_number=(
                diagnosis.reference_lap_number
            ),
            target_lap_number=(
                diagnosis.target_lap_number
            ),
            trend=self._trend(
                net_delta
            ),
            total_time_lost_seconds=(
                total_loss
            ),
            total_time_gained_seconds=(
                total_gain
            ),
            net_time_delta_seconds=(
                net_delta
            ),
            corners_analyzed=(
                diagnosis.diagnosed_corner_count
            ),
            corners_with_time_loss=(
                diagnosis.corners_with_time_loss
            ),
            corners_with_issues=(
                diagnosis.corners_with_issues
            ),
            recommendations_generated=(
                recommendations
                .recommendation_count
            ),
            recommendations_selected=(
                coaching_plan
                .recommendations_selected
            ),
            recommendations_suppressed=(
                coaching_plan
                .recommendations_suppressed
            ),
            primary_problem_corner=(
                primary_problem_corner
            ),
            corners=self._corner_summaries(
                diagnosis
            ),
            focuses=self._focus_summaries(
                coaching_plan
            ),
        )