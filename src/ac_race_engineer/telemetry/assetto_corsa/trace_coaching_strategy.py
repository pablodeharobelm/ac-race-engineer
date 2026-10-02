from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    DrivingPhase,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    DrivingRecommendation,
    DrivingRecommendationReport,
    DrivingRecommendationType,
)


class CoachingFocusLevel(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class CoachingFocus:
    rank: int
    focus_level: CoachingFocusLevel

    recommendation: DrivingRecommendation

    impact_score: float

    @property
    def corner_number(
        self,
    ) -> int:
        return self.recommendation.corner_number

    @property
    def recommendation_type(
        self,
    ) -> DrivingRecommendationType:
        return (
            self.recommendation
            .recommendation_type
        )

    @property
    def phase(
        self,
    ) -> DrivingPhase:
        return self.recommendation.phase

    @property
    def title(
        self,
    ) -> str:
        return self.recommendation.title

    @property
    def instruction(
        self,
    ) -> str:
        return self.recommendation.instruction


@dataclass(frozen=True)
class CoachingPlan:
    reference_lap_number: int
    target_lap_number: int

    focuses: tuple[
        CoachingFocus,
        ...,
    ]

    recommendations_considered: int
    recommendations_selected: int
    recommendations_suppressed: int

    total_time_loss_seconds: float

    @property
    def primary_focus(
        self,
    ) -> CoachingFocus | None:
        if not self.focuses:
            return None

        return self.focuses[0]

    @property
    def affected_corner_count(
        self,
    ) -> int:
        return len(
            {
                focus.corner_number
                for focus in self.focuses
            }
        )


class AssettoCorsaCoachingStrategyService:
    """
    Convert driving recommendations into a concise
    coaching strategy.

    Responsibilities:

    - prioritize recommendations,
    - suppress redundant advice,
    - limit cognitive load,
    - select the highest-impact actions,
    - preserve deterministic evidence.

    This service does not invent new diagnoses or advice.
    """

    def __init__(
        self,
        *,
        maximum_focuses: int = 3,
        maximum_focuses_per_corner: int = 2,
    ) -> None:
        if maximum_focuses <= 0:
            raise ValueError(
                "maximum_focuses must be "
                "greater than 0"
            )

        if maximum_focuses_per_corner <= 0:
            raise ValueError(
                "maximum_focuses_per_corner must "
                "be greater than 0"
            )

        self.maximum_focuses = (
            maximum_focuses
        )

        self.maximum_focuses_per_corner = (
            maximum_focuses_per_corner
        )

    @staticmethod
    def _priority_weight(
        priority: RecommendationPriority,
    ) -> float:
        weights = {
            RecommendationPriority.HIGH: 3.0,
            RecommendationPriority.MEDIUM: 2.0,
            RecommendationPriority.LOW: 1.0,
        }

        return weights[
            priority
        ]

    def _impact_score(
        self,
        recommendation: DrivingRecommendation,
    ) -> float:
        priority_weight = (
            self._priority_weight(
                recommendation.priority
            )
        )

        corner_loss = max(
            0.0,
            recommendation
            .corner_time_loss_seconds,
        )

        diagnostic_loss = max(
            0.0,
            recommendation
            .diagnostic_time_loss_seconds,
        )

        return (
            corner_loss * 10.0
            + diagnostic_loss * 5.0
            + priority_weight
        )

    def _deduplicate(
        self,
        recommendations: tuple[
            DrivingRecommendation,
            ...,
        ],
    ) -> tuple[
        DrivingRecommendation,
        ...,
    ]:
        best_by_key: dict[
            tuple[
                int,
                DrivingRecommendationType,
            ],
            DrivingRecommendation,
        ] = {}

        for recommendation in recommendations:
            key = (
                recommendation.corner_number,
                recommendation.recommendation_type,
            )

            current = best_by_key.get(
                key
            )

            if current is None:
                best_by_key[
                    key
                ] = recommendation
                continue

            current_score = (
                self._impact_score(
                    current
                )
            )

            candidate_score = (
                self._impact_score(
                    recommendation
                )
            )

            if (
                candidate_score
                > current_score
            ):
                best_by_key[
                    key
                ] = recommendation

        return tuple(
            best_by_key.values()
        )

    def _sorted_candidates(
        self,
        recommendations: tuple[
            DrivingRecommendation,
            ...,
        ],
    ) -> tuple[
        DrivingRecommendation,
        ...,
    ]:
        return tuple(
            sorted(
                recommendations,
                key=lambda recommendation: (
                    -self._impact_score(
                        recommendation
                    ),
                    recommendation.corner_number,
                    recommendation.phase.value,
                    recommendation
                    .recommendation_type
                    .value,
                ),
            )
        )

    def _select(
        self,
        candidates: tuple[
            DrivingRecommendation,
            ...,
        ],
    ) -> tuple[
        DrivingRecommendation,
        ...,
    ]:
        selected: list[
            DrivingRecommendation
        ] = []

        per_corner: dict[
            int,
            int,
        ] = {}

        for recommendation in candidates:
            if (
                len(selected)
                >= self.maximum_focuses
            ):
                break

            corner_number = (
                recommendation.corner_number
            )

            current_count = (
                per_corner.get(
                    corner_number,
                    0,
                )
            )

            if (
                current_count
                >= self.maximum_focuses_per_corner
            ):
                continue

            selected.append(
                recommendation
            )

            per_corner[
                corner_number
            ] = (
                current_count + 1
            )

        return tuple(
            selected
        )

    @staticmethod
    def _focus_level(
        rank: int,
    ) -> CoachingFocusLevel:
        if rank == 1:
            return CoachingFocusLevel.PRIMARY

        if rank == 2:
            return CoachingFocusLevel.SECONDARY

        return CoachingFocusLevel.OPTIONAL

    def build_plan(
        self,
        report: DrivingRecommendationReport,
    ) -> CoachingPlan:
        deduplicated = self._deduplicate(
            report.recommendations
        )

        candidates = (
            self._sorted_candidates(
                deduplicated
            )
        )

        selected = self._select(
            candidates
        )

        focuses = tuple(
            CoachingFocus(
                rank=rank,
                focus_level=self._focus_level(
                    rank
                ),
                recommendation=(
                    recommendation
                ),
                impact_score=(
                    self._impact_score(
                        recommendation
                    )
                ),
            )
            for rank, recommendation
            in enumerate(
                selected,
                start=1,
            )
        )

        return CoachingPlan(
            reference_lap_number=(
                report.reference_lap_number
            ),
            target_lap_number=(
                report.target_lap_number
            ),
            focuses=focuses,
            recommendations_considered=len(
                report.recommendations
            ),
            recommendations_selected=len(
                focuses
            ),
            recommendations_suppressed=(
                len(
                    report.recommendations
                )
                - len(
                    focuses
                )
            ),
            total_time_loss_seconds=(
                report.total_time_loss_seconds
            ),
        )