from dataclasses import dataclass
from enum import StrEnum

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


class DrivingRecommendationType(StrEnum):
    BRAKING_POINT = "braking_point"
    BRAKE_RELEASE = "brake_release"
    BRAKE_PRESSURE = "brake_pressure"

    MINIMUM_SPEED = "minimum_speed"

    TURN_IN = "turn_in"
    TRAIL_BRAKING = "trail_braking"
    STEERING_INPUT = "steering_input"
    APEX_SPEED = "apex_speed"

    THROTTLE_APPLICATION = (
        "throttle_application"
    )
    EXIT_SPEED = "exit_speed"
    STEERING_UNWIND = "steering_unwind"


@dataclass(frozen=True)
class DrivingRecommendation:
    recommendation_type: (
        DrivingRecommendationType
    )

    priority: RecommendationPriority

    corner_number: int
    phase: DrivingPhase

    source: DrivingDiagnosticSource
    diagnostic_code: str

    title: str
    instruction: str
    rationale: str

    corner_time_loss_seconds: float
    diagnostic_time_loss_seconds: float

    minimum_speed_delta_kmh: float
    apex_speed_delta_kmh: float
    exit_speed_delta_kmh: float


@dataclass(frozen=True)
class DrivingRecommendationReport:
    reference_lap_number: int
    target_lap_number: int

    recommendations: tuple[
        DrivingRecommendation,
        ...,
    ]

    corners_analyzed: int
    corners_with_recommendations: int

    unmapped_issue_count: int

    total_time_loss_seconds: float

    @property
    def recommendation_count(
        self,
    ) -> int:
        return len(
            self.recommendations
        )

    def for_corner(
        self,
        corner_number: int,
    ) -> tuple[
        DrivingRecommendation,
        ...,
    ]:
        return tuple(
            recommendation
            for recommendation
            in self.recommendations
            if (
                recommendation.corner_number
                == corner_number
            )
        )


@dataclass(frozen=True)
class _RecommendationTemplate:
    recommendation_type: (
        DrivingRecommendationType
    )

    phase: DrivingPhase

    title: str
    instruction: str
    rationale: str


class AssettoCorsaDrivingRecommendationService:
    """
    Convert deterministic driving diagnoses into
    structured coaching recommendations.

    The service never creates recommendations directly
    from raw telemetry.

    Recommendations are only generated from issues that
    have already been produced by the deterministic
    driving-diagnosis pipeline.

    This keeps the architecture:

        telemetry
            ->
        measurement
            ->
        comparison
            ->
        diagnosis
            ->
        recommendation
    """

    def __init__(
        self,
        *,
        minimum_corner_time_loss_seconds: float = 0.05,
    ) -> None:
        if (
            minimum_corner_time_loss_seconds
            < 0.0
        ):
            raise ValueError(
                "minimum_corner_time_loss_seconds "
                "cannot be negative"
            )

        self.minimum_corner_time_loss_seconds = (
            minimum_corner_time_loss_seconds
        )

    @staticmethod
    def _priority(
        severity: str,
    ) -> RecommendationPriority:
        if severity == "HIGH":
            return RecommendationPriority.HIGH

        if severity == "MEDIUM":
            return RecommendationPriority.MEDIUM

        return RecommendationPriority.LOW

    @staticmethod
    def _template_for_issue(
        issue: DrivingIssue,
    ) -> _RecommendationTemplate | None:
        key = (
            issue.source,
            issue.code,
        )

        if key == (
            DrivingDiagnosticSource.BRAKING,
            "BRAKING_TOO_EARLY",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKING_POINT
                ),
                phase=DrivingPhase.ENTRY,
                title="Brake slightly later",
                instruction=(
                    "Move the braking point slightly "
                    "later while preserving a stable "
                    "entry into the corner."
                ),
                rationale=(
                    "The target lap begins braking "
                    "earlier than the reference in a "
                    "time-losing corner."
                ),
            )

        if key == (
            DrivingDiagnosticSource.BRAKING,
            "BRAKING_TOO_LATE",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKING_POINT
                ),
                phase=DrivingPhase.ENTRY,
                title="Brake slightly earlier",
                instruction=(
                    "Move the braking point slightly "
                    "earlier to improve control before "
                    "turn-in."
                ),
                rationale=(
                    "The target lap begins braking "
                    "later than the reference and loses "
                    "time through the corner."
                ),
            )

        if key == (
            DrivingDiagnosticSource.BRAKING,
            "OVER_SLOWING",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .MINIMUM_SPEED
                ),
                phase=DrivingPhase.ENTRY,
                title="Carry more minimum speed",
                instruction=(
                    "Reduce unnecessary deceleration "
                    "and aim to preserve more speed "
                    "through the slowest part of the "
                    "corner."
                ),
                rationale=(
                    "The target lap reaches a lower "
                    "minimum speed than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.BRAKING,
            "LATE_BRAKE_RELEASE",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKE_RELEASE
                ),
                phase=DrivingPhase.ENTRY,
                title="Release the brake earlier",
                instruction=(
                    "Begin releasing the brake earlier "
                    "and reduce brake pressure "
                    "progressively approaching turn-in."
                ),
                rationale=(
                    "The target lap keeps braking for "
                    "longer than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.BRAKING,
            "EXCESSIVE_BRAKE_PRESSURE",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKE_PRESSURE
                ),
                phase=DrivingPhase.ENTRY,
                title="Reduce brake pressure",
                instruction=(
                    "Use less brake pressure where "
                    "possible and focus on a smoother "
                    "deceleration profile."
                ),
                rationale=(
                    "The target lap applies more brake "
                    "pressure than the reference in a "
                    "time-losing braking zone."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "EARLY_TURN_IN",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .TURN_IN
                ),
                phase=DrivingPhase.ENTRY,
                title="Delay turn-in slightly",
                instruction=(
                    "Wait slightly longer before "
                    "starting the steering input."
                ),
                rationale=(
                    "The target lap turns into the "
                    "corner earlier than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "LATE_TURN_IN",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .TURN_IN
                ),
                phase=DrivingPhase.ENTRY,
                title="Turn in slightly earlier",
                instruction=(
                    "Begin the steering input slightly "
                    "earlier while maintaining a "
                    "controlled entry."
                ),
                rationale=(
                    "The target lap turns into the "
                    "corner later than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "ENTRY_OVER_SLOWING",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .MINIMUM_SPEED
                ),
                phase=DrivingPhase.ENTRY,
                title="Reduce entry speed loss",
                instruction=(
                    "Preserve more speed between "
                    "turn-in and apex instead of "
                    "continuing to decelerate "
                    "unnecessarily."
                ),
                rationale=(
                    "The target lap loses more speed "
                    "between turn-in and apex than the "
                    "reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "EXCESSIVE_TRAIL_BRAKING",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .TRAIL_BRAKING
                ),
                phase=DrivingPhase.ENTRY,
                title="Reduce brake carried into turn-in",
                instruction=(
                    "Release brake pressure more "
                    "progressively as steering input "
                    "increases."
                ),
                rationale=(
                    "The target lap carries more brake "
                    "into the corner than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "EXCESSIVE_STEERING",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .STEERING_INPUT
                ),
                phase=DrivingPhase.ENTRY,
                title="Reduce steering input",
                instruction=(
                    "Use less unnecessary steering "
                    "angle and aim for a smoother "
                    "steering progression."
                ),
                rationale=(
                    "The target lap requires more "
                    "steering input than the reference "
                    "during corner entry."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_ENTRY,
            "POOR_APEX_SPEED",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .APEX_SPEED
                ),
                phase=DrivingPhase.ENTRY,
                title="Improve apex speed",
                instruction=(
                    "Focus on preserving more speed "
                    "through the apex without "
                    "compromising stability."
                ),
                rationale=(
                    "The target lap reaches the apex "
                    "at a lower speed than the "
                    "reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_EXIT,
            "LATE_THROTTLE_APPLICATION",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .THROTTLE_APPLICATION
                ),
                phase=DrivingPhase.EXIT,
                title="Apply throttle earlier",
                instruction=(
                    "Begin progressive throttle "
                    "application earlier once the car "
                    "is stable and steering angle "
                    "allows it."
                ),
                rationale=(
                    "The target lap begins meaningful "
                    "throttle application later than "
                    "the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_EXIT,
            "POOR_EXIT_SPEED",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .EXIT_SPEED
                ),
                phase=DrivingPhase.EXIT,
                title="Prioritize exit speed",
                instruction=(
                    "Focus on preserving acceleration "
                    "from the apex and carrying more "
                    "speed out of the corner."
                ),
                rationale=(
                    "The target lap exits the corner "
                    "slower than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_EXIT,
            "LOW_EXIT_THROTTLE",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .THROTTLE_APPLICATION
                ),
                phase=DrivingPhase.EXIT,
                title="Increase exit throttle",
                instruction=(
                    "Increase throttle progressively "
                    "as the steering angle reduces and "
                    "available grip permits."
                ),
                rationale=(
                    "The target lap uses less throttle "
                    "at corner exit than the reference."
                ),
            )

        if key == (
            DrivingDiagnosticSource.CORNER_EXIT,
            "SLOW_STEERING_UNWIND",
        ):
            return _RecommendationTemplate(
                recommendation_type=(
                    DrivingRecommendationType
                    .STEERING_UNWIND
                ),
                phase=DrivingPhase.EXIT,
                title="Unwind steering sooner",
                instruction=(
                    "Reduce steering angle more "
                    "progressively through the exit to "
                    "support earlier acceleration."
                ),
                rationale=(
                    "The target lap keeps more steering "
                    "angle through the exit than the "
                    "reference."
                ),
            )

        return None

    def _build_recommendation(
        self,
        *,
        corner: CornerDrivingDiagnosis,
        issue: DrivingIssue,
    ) -> DrivingRecommendation | None:
        template = (
            self._template_for_issue(
                issue
            )
        )

        if template is None:
            return None

        return DrivingRecommendation(
            recommendation_type=(
                template.recommendation_type
            ),
            priority=self._priority(
                issue.severity
            ),
            corner_number=(
                corner.reference_corner_number
            ),
            phase=template.phase,
            source=issue.source,
            diagnostic_code=issue.code,
            title=template.title,
            instruction=template.instruction,
            rationale=template.rationale,
            corner_time_loss_seconds=(
                corner.time_lost_seconds
            ),
            diagnostic_time_loss_seconds=(
                issue
                .diagnostic_time_loss_seconds
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
        )

    def generate(
        self,
        diagnosis: RealDrivingDiagnosisReport,
    ) -> DrivingRecommendationReport:
        recommendations: list[
            DrivingRecommendation
        ] = []

        unmapped_issue_count = 0

        corners_with_recommendations: set[
            int
        ] = set()

        for corner in diagnosis.corners:
            if (
                corner.time_lost_seconds
                < self.minimum_corner_time_loss_seconds
            ):
                continue

            for issue in corner.issues:
                recommendation = (
                    self._build_recommendation(
                        corner=corner,
                        issue=issue,
                    )
                )

                if recommendation is None:
                    unmapped_issue_count += 1
                    continue

                recommendations.append(
                    recommendation
                )

                corners_with_recommendations.add(
                    corner.reference_corner_number
                )

        recommendations.sort(
            key=lambda recommendation: (
                recommendation.corner_number,
                recommendation.phase.value,
                recommendation.source.value,
                recommendation.diagnostic_code,
            )
        )

        return DrivingRecommendationReport(
            reference_lap_number=(
                diagnosis.reference_lap_number
            ),
            target_lap_number=(
                diagnosis.target_lap_number
            ),
            recommendations=tuple(
                recommendations
            ),
            corners_analyzed=(
                diagnosis.diagnosed_corner_count
            ),
            corners_with_recommendations=len(
                corners_with_recommendations
            ),
            unmapped_issue_count=(
                unmapped_issue_count
            ),
            total_time_loss_seconds=(
                diagnosis
                .total_time_lost_seconds
            ),
        )