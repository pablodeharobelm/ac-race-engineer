from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.diagnostics import (
    LapComparisonDiagnosis,
)


class RecommendationPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationType(StrEnum):
    PRIMARY_SECTOR = "primary_sector"
    SECONDARY_SECTOR = "secondary_sector"
    CONSOLIDATE_GAIN = "consolidate_gain"
    DATA_QUALITY = "data_quality"
    BALANCED_IMPROVEMENT = "balanced_improvement"


@dataclass(frozen=True)
class RaceEngineerRecommendation:
    recommendation_type: RecommendationType

    priority: RecommendationPriority

    sector_number: int | None

    title: str
    message: str

    evidence: tuple[str, ...]


@dataclass(frozen=True)
class RaceEngineerRecommendationSet:
    session_id: str

    reference_lap_number: int
    target_lap_number: int

    recommendations: tuple[
        RaceEngineerRecommendation,
        ...,
    ]


class AssettoCorsaRecommendationService:
    """
    Convert deterministic timing diagnostics into
    structured recommendations.

    This service does not infer driving causes.

    It only recommends where to focus based on
    measured timing deltas and data quality.
    """

    @staticmethod
    def _format_seconds(
        milliseconds: int,
    ) -> str:
        return (
            f"{milliseconds / 1000.0:.3f} s"
        )

    @staticmethod
    def _priority_from_share(
        share: float | None,
    ) -> RecommendationPriority:
        if share is None:
            return RecommendationPriority.MEDIUM

        if share >= 0.60:
            return RecommendationPriority.HIGH

        if share >= 0.30:
            return RecommendationPriority.MEDIUM

        return RecommendationPriority.LOW

    def _data_quality_recommendation(
        self,
        diagnosis: LapComparisonDiagnosis,
    ) -> RaceEngineerRecommendation | None:
        if (
            diagnosis.complete_sector_data
            and diagnosis.sector_delta_matches_lap_delta
        ):
            return None

        evidence: list[str] = []

        if not diagnosis.complete_sector_data:
            evidence.append(
                "Sector data is incomplete."
            )

        if (
            not diagnosis.sector_delta_matches_lap_delta
        ):
            evidence.append(
                "Sector deltas do not fully explain "
                "the lap delta."
            )

            evidence.append(
                "Unexplained delta: "
                f"{self._format_seconds(abs(diagnosis.unexplained_delta_ms))}"
            )

        return RaceEngineerRecommendation(
            recommendation_type=(
                RecommendationType.DATA_QUALITY
            ),
            priority=(
                RecommendationPriority.HIGH
            ),
            sector_number=None,
            title="Review telemetry data quality",
            message=(
                "Do not draw detailed driving conclusions "
                "from this comparison until the missing or "
                "inconsistent timing data is resolved."
            ),
            evidence=tuple(
                evidence
            ),
        )

    def _primary_loss_recommendation(
        self,
        diagnosis: LapComparisonDiagnosis,
    ) -> RaceEngineerRecommendation | None:
        sector = (
            diagnosis.primary_loss_sector
        )

        if sector is None:
            return None

        priority = (
            self._priority_from_share(
                diagnosis.primary_loss_share
            )
        )

        share_text = "unknown"

        if (
            diagnosis.primary_loss_share
            is not None
        ):
            share_text = (
                f"{diagnosis.primary_loss_share * 100.0:.1f}%"
            )

        return RaceEngineerRecommendation(
            recommendation_type=(
                RecommendationType.PRIMARY_SECTOR
            ),
            priority=priority,
            sector_number=sector,
            title=(
                f"Prioritize Sector {sector}"
            ),
            message=(
                f"Sector {sector} is the largest "
                "measured source of lost time. "
                "Prioritize this sector before making "
                "broader changes to the lap."
            ),
            evidence=(
                (
                    "Time lost in sector: "
                    f"{self._format_seconds(diagnosis.primary_loss_ms)}"
                ),
                (
                    "Share of total measured lost time: "
                    f"{share_text}"
                ),
            ),
        )

    def _secondary_loss_recommendation(
        self,
        diagnosis: LapComparisonDiagnosis,
    ) -> RaceEngineerRecommendation | None:
        if len(
            diagnosis.lost_sectors
        ) < 2:
            return None

        sector = (
            diagnosis.lost_sectors[1]
        )

        return RaceEngineerRecommendation(
            recommendation_type=(
                RecommendationType.SECONDARY_SECTOR
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            sector_number=(
                sector.sector_number
            ),
            title=(
                "Secondary improvement area: "
                f"Sector {sector.sector_number}"
            ),
            message=(
                f"After working on the main loss, "
                f"review Sector {sector.sector_number} "
                "as the next timing priority."
            ),
            evidence=(
                (
                    "Measured loss: "
                    f"{self._format_seconds(sector.delta_ms)}"
                ),
            ),
        )

    def _gain_recommendation(
        self,
        diagnosis: LapComparisonDiagnosis,
    ) -> RaceEngineerRecommendation | None:
        sector = (
            diagnosis.primary_gain_sector
        )

        if sector is None:
            return None

        return RaceEngineerRecommendation(
            recommendation_type=(
                RecommendationType.CONSOLIDATE_GAIN
            ),
            priority=(
                RecommendationPriority.LOW
            ),
            sector_number=sector,
            title=(
                f"Preserve the gain in Sector {sector}"
            ),
            message=(
                f"Sector {sector} improved relative "
                "to the reference lap. Preserve what "
                "worked there while focusing changes "
                "on slower sectors."
            ),
            evidence=(
                (
                    "Measured gain: "
                    f"{self._format_seconds(diagnosis.primary_gain_ms)}"
                ),
            ),
        )

    def _balanced_recommendation(
        self,
        diagnosis: LapComparisonDiagnosis,
    ) -> RaceEngineerRecommendation | None:
        if not diagnosis.has_actionable_sector_data:
            return None

        if (
            diagnosis.primary_loss_share
            is not None
            and diagnosis.primary_loss_share
            >= 0.60
        ):
            return None

        if len(
            diagnosis.lost_sectors
        ) < 2:
            return None

        return RaceEngineerRecommendation(
            recommendation_type=(
                RecommendationType.BALANCED_IMPROVEMENT
            ),
            priority=(
                RecommendationPriority.MEDIUM
            ),
            sector_number=None,
            title="Improve multiple sectors",
            message=(
                "The measured time loss is distributed "
                "across several sectors rather than being "
                "dominated by one area. Work on the slower "
                "sectors in order of measured loss."
            ),
            evidence=tuple(
                (
                    f"S{sector.sector_number}: "
                    f"{self._format_seconds(sector.delta_ms)} lost"
                )
                for sector in diagnosis.lost_sectors
            ),
        )

    def generate(
        self,
        diagnosis: LapComparisonDiagnosis,
    ) -> RaceEngineerRecommendationSet:
        recommendations: list[
            RaceEngineerRecommendation
        ] = []

        data_quality = (
            self._data_quality_recommendation(
                diagnosis
            )
        )

        if data_quality is not None:
            recommendations.append(
                data_quality
            )

        if diagnosis.has_actionable_sector_data:
            primary = (
                self._primary_loss_recommendation(
                    diagnosis
                )
            )

            if primary is not None:
                recommendations.append(
                    primary
                )

            secondary = (
                self._secondary_loss_recommendation(
                    diagnosis
                )
            )

            if secondary is not None:
                recommendations.append(
                    secondary
                )

            balanced = (
                self._balanced_recommendation(
                    diagnosis
                )
            )

            if balanced is not None:
                recommendations.append(
                    balanced
                )

            gain = (
                self._gain_recommendation(
                    diagnosis
                )
            )

            if gain is not None:
                recommendations.append(
                    gain
                )

        recommendations.sort(
            key=self._priority_sort_key
        )

        return RaceEngineerRecommendationSet(
            session_id=(
                diagnosis.session_id
            ),
            reference_lap_number=(
                diagnosis.reference_lap_number
            ),
            target_lap_number=(
                diagnosis.target_lap_number
            ),
            recommendations=tuple(
                recommendations
            ),
        )

    @staticmethod
    def _priority_sort_key(
        recommendation: RaceEngineerRecommendation,
    ) -> int:
        priorities = {
            RecommendationPriority.HIGH: 0,
            RecommendationPriority.MEDIUM: 1,
            RecommendationPriority.LOW: 2,
        }

        return priorities[
            recommendation.priority
        ]