from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AssettoCorsaTraceComparisonService,
    DrivingTraceSample,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    AssettoCorsaBrakingZoneService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking_comparison import (
    AssettoCorsaBrakingComparisonService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking_diagnostics import (
    AssettoCorsaBrakingDiagnosticService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    AssettoCorsaCoachingStrategyService,
    CoachingPlan,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    AssettoCorsaCornerEntryService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_comparison import (
    AssettoCorsaCornerEntryComparisonService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_diagnostics import (
    AssettoCorsaCornerEntryDiagnosticService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit import (
    AssettoCorsaCornerExitService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_comparison import (
    AssettoCorsaCornerExitComparisonService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_diagnostics import (
    AssettoCorsaCornerExitDiagnosticService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    AssettoCorsaRealDrivingDiagnosticService,
    RealDrivingDiagnosisReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    AssettoCorsaDrivingRecommendationService,
    DrivingRecommendationReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_llm import (
    AssettoCorsaRaceEngineerExplanationService,
    RaceEngineerExplanation,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
    AssettoCorsaRaceEngineerReportService,
    RaceEngineerReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation import (
    AssettoCorsaTrackSegmentationService,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation_comparison import (
    AssettoCorsaTrackSegmentationComparisonService,
)


@dataclass(frozen=True)
class RaceEngineerPipelineResult:
    """
    Final result of the complete driving-analysis
    pipeline.

    Intermediate high-level results are intentionally
    preserved so callers can:

    - inspect/debug the analysis,
    - expose structured data through an API,
    - build a UI,
    - persist results,
    - generate an optional LLM explanation.
    """

    trace_comparison: LapTraceComparison

    diagnosis: RealDrivingDiagnosisReport

    recommendations: DrivingRecommendationReport

    coaching_plan: CoachingPlan

    report: RaceEngineerReport

    explanation: RaceEngineerExplanation | None


class AssettoCorsaRaceEngineerPipeline:
    """
    End-to-end deterministic Assetto Corsa driving
    analysis pipeline.

    Pipeline:

        reference + target traces
            ->
        aligned trace comparison
            ->
        braking analysis
            ->
        corner-entry analysis
            ->
        corner-exit analysis
            ->
        track segmentation
            ->
        unified driving diagnosis
            ->
        recommendations
            ->
        coaching strategy
            ->
        race-engineer report
            ->
        optional LLM explanation

    The LLM is deliberately kept at the final layer.

    All measurements, diagnoses, recommendations and
    prioritization happen before the LLM is called.
    """

    def __init__(
        self,
        *,
        trace_comparison_service: (
            AssettoCorsaTraceComparisonService
            | None
        ) = None,
        braking_zone_service: (
            AssettoCorsaBrakingZoneService
            | None
        ) = None,
        braking_comparison_service: (
            AssettoCorsaBrakingComparisonService
            | None
        ) = None,
        braking_diagnostic_service: (
            AssettoCorsaBrakingDiagnosticService
            | None
        ) = None,
        corner_entry_service: (
            AssettoCorsaCornerEntryService
            | None
        ) = None,
        corner_entry_comparison_service: (
            AssettoCorsaCornerEntryComparisonService
            | None
        ) = None,
        corner_entry_diagnostic_service: (
            AssettoCorsaCornerEntryDiagnosticService
            | None
        ) = None,
        corner_exit_service: (
            AssettoCorsaCornerExitService
            | None
        ) = None,
        corner_exit_comparison_service: (
            AssettoCorsaCornerExitComparisonService
            | None
        ) = None,
        corner_exit_diagnostic_service: (
            AssettoCorsaCornerExitDiagnosticService
            | None
        ) = None,
        segmentation_service: (
            AssettoCorsaTrackSegmentationService
            | None
        ) = None,
        segmentation_comparison_service: (
            AssettoCorsaTrackSegmentationComparisonService
            | None
        ) = None,
        driving_diagnostic_service: (
            AssettoCorsaRealDrivingDiagnosticService
            | None
        ) = None,
        recommendation_service: (
            AssettoCorsaDrivingRecommendationService
            | None
        ) = None,
        coaching_service: (
            AssettoCorsaCoachingStrategyService
            | None
        ) = None,
        report_service: (
            AssettoCorsaRaceEngineerReportService
            | None
        ) = None,
        explanation_service: (
            AssettoCorsaRaceEngineerExplanationService
            | None
        ) = None,
    ) -> None:
        self.trace_comparison_service = (
            trace_comparison_service
            or AssettoCorsaTraceComparisonService()
        )

        self.braking_zone_service = (
            braking_zone_service
            or AssettoCorsaBrakingZoneService()
        )

        self.braking_comparison_service = (
            braking_comparison_service
            or AssettoCorsaBrakingComparisonService()
        )

        self.braking_diagnostic_service = (
            braking_diagnostic_service
            or AssettoCorsaBrakingDiagnosticService()
        )

        self.corner_entry_service = (
            corner_entry_service
            or AssettoCorsaCornerEntryService()
        )

        self.corner_entry_comparison_service = (
            corner_entry_comparison_service
            or AssettoCorsaCornerEntryComparisonService()
        )

        self.corner_entry_diagnostic_service = (
            corner_entry_diagnostic_service
            or AssettoCorsaCornerEntryDiagnosticService()
        )

        self.corner_exit_service = (
            corner_exit_service
            or AssettoCorsaCornerExitService()
        )

        self.corner_exit_comparison_service = (
            corner_exit_comparison_service
            or AssettoCorsaCornerExitComparisonService()
        )

        self.corner_exit_diagnostic_service = (
            corner_exit_diagnostic_service
            or AssettoCorsaCornerExitDiagnosticService()
        )

        self.segmentation_service = (
            segmentation_service
            or AssettoCorsaTrackSegmentationService()
        )

        self.segmentation_comparison_service = (
            segmentation_comparison_service
            or AssettoCorsaTrackSegmentationComparisonService()
        )

        self.driving_diagnostic_service = (
            driving_diagnostic_service
            or AssettoCorsaRealDrivingDiagnosticService()
        )

        self.recommendation_service = (
            recommendation_service
            or AssettoCorsaDrivingRecommendationService()
        )

        self.coaching_service = (
            coaching_service
            or AssettoCorsaCoachingStrategyService()
        )

        self.report_service = (
            report_service
            or AssettoCorsaRaceEngineerReportService()
        )

        self.explanation_service = (
            explanation_service
        )

    def run(
        self,
        *,
        reference_lap_number: int,
        target_lap_number: int,
        reference_trace: tuple[
            DrivingTraceSample,
            ...,
        ],
        target_trace: tuple[
            DrivingTraceSample,
            ...,
        ],
        grid_points: int = 201,
        explain: bool = False,
        language: str = "es",
    ) -> RaceEngineerPipelineResult:
        trace_comparison = (
            self.trace_comparison_service.compare(
                reference_lap_number=(
                    reference_lap_number
                ),
                target_lap_number=(
                    target_lap_number
                ),
                reference_trace=(
                    reference_trace
                ),
                target_trace=(
                    target_trace
                ),
                grid_points=grid_points,
            )
        )

        reference_braking_zones = (
            self.braking_zone_service.analyze(
                reference_trace
            )
        )

        target_braking_zones = (
            self.braking_zone_service.analyze(
                target_trace
            )
        )

        braking_comparison = (
            self.braking_comparison_service.compare(
                reference_zones=(
                    reference_braking_zones
                ),
                target_zones=(
                    target_braking_zones
                ),
                trace_comparison=(
                    trace_comparison
                ),
            )
        )

        braking_report = (
            self.braking_diagnostic_service.analyze(
                braking_comparison
            )
        )

        reference_entries = (
            self.corner_entry_service.analyze(
                samples=reference_trace,
                braking_zones=(
                    reference_braking_zones
                ),
            )
        )

        target_entries = (
            self.corner_entry_service.analyze(
                samples=target_trace,
                braking_zones=(
                    target_braking_zones
                ),
            )
        )

        entry_comparison = (
            self.corner_entry_comparison_service.compare(
                reference_entries=(
                    reference_entries
                ),
                target_entries=(
                    target_entries
                ),
                trace_comparison=(
                    trace_comparison
                ),
            )
        )

        entry_report = (
            self.corner_entry_diagnostic_service.analyze(
                entry_comparison
            )
        )

        reference_exits = (
            self.corner_exit_service.analyze(
                samples=reference_trace,
                entries=reference_entries,
            )
        )

        target_exits = (
            self.corner_exit_service.analyze(
                samples=target_trace,
                entries=target_entries,
            )
        )

        exit_comparison = (
            self.corner_exit_comparison_service.compare(
                reference_exits=(
                    reference_exits
                ),
                target_exits=(
                    target_exits
                ),
                trace_comparison=(
                    trace_comparison
                ),
            )
        )

        exit_report = (
            self.corner_exit_diagnostic_service.analyze(
                exit_comparison
            )
        )

        reference_segmentation = (
            self.segmentation_service.segment(
                braking_zones=(
                    reference_braking_zones
                ),
                entries=reference_entries,
                exits=reference_exits,
            )
        )

        target_segmentation = (
            self.segmentation_service.segment(
                braking_zones=(
                    target_braking_zones
                ),
                entries=target_entries,
                exits=target_exits,
            )
        )

        segmentation_comparison = (
            self.segmentation_comparison_service.compare(
                reference_corners=(
                    reference_segmentation.corners
                ),
                target_corners=(
                    target_segmentation.corners
                ),
                trace_comparison=(
                    trace_comparison
                ),
            )
        )

        diagnosis = (
            self.driving_diagnostic_service.analyze(
                segmentation=(
                    segmentation_comparison
                ),
                braking_report=(
                    braking_report
                ),
                entry_report=(
                    entry_report
                ),
                exit_report=(
                    exit_report
                ),
            )
        )

        recommendations = (
            self.recommendation_service.generate(
                diagnosis
            )
        )

        coaching_plan = (
            self.coaching_service.build_plan(
                recommendations
            )
        )

        report = (
            self.report_service.build(
                diagnosis=diagnosis,
                recommendations=(
                    recommendations
                ),
                coaching_plan=(
                    coaching_plan
                ),
            )
        )

        explanation = None

        if explain:
            if (
                self.explanation_service
                is None
            ):
                raise ValueError(
                    "explain=True requires an "
                    "explanation_service"
                )

            explanation = (
                self.explanation_service.explain(
                    report,
                    language=language,
                )
            )

        return RaceEngineerPipelineResult(
            trace_comparison=(
                trace_comparison
            ),
            diagnosis=diagnosis,
            recommendations=(
                recommendations
            ),
            coaching_plan=(
                coaching_plan
            ),
            report=report,
            explanation=explanation,
        )
