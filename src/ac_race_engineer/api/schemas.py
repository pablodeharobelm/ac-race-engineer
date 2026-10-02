from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ac_race_engineer.database.race_engineer_analyses import (
    RaceEngineerAnalysisRecord,
)
from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_pipeline import (
    RaceEngineerPipelineResult,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class DrivingTraceSampleRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    progress: float = Field(
        ge=0.0,
        le=1.0,
    )

    elapsed_seconds: float = Field(
        ge=0.0,
    )

    speed_kmh: float = Field(
        ge=0.0,
    )

    throttle: float = Field(
        ge=0.0,
        le=1.0,
    )

    brake: float = Field(
        ge=0.0,
        le=1.0,
    )

    steering_angle_deg: float

    def to_domain(
        self,
    ) -> DrivingTraceSample:
        return DrivingTraceSample(
            progress=self.progress,
            elapsed_seconds=(
                self.elapsed_seconds
            ),
            speed_kmh=self.speed_kmh,
            throttle=self.throttle,
            brake=self.brake,
            steering_angle_deg=(
                self.steering_angle_deg
            ),
        )


class RaceEngineerAnalysisRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    reference_lap_number: int = Field(
        gt=0,
    )

    target_lap_number: int = Field(
        gt=0,
    )

    reference_trace: list[
        DrivingTraceSampleRequest
    ] = Field(
        min_length=2,
    )

    target_trace: list[
        DrivingTraceSampleRequest
    ] = Field(
        min_length=2,
    )

    grid_points: int = Field(
        default=201,
        ge=2,
        le=5001,
    )

    explain: bool = False

    language: str = Field(
        default="es",
        min_length=1,
        max_length=16,
    )

    persist: bool = False

    session_id: str | None = Field(
        default=None,
        max_length=64,
    )


class RaceEngineerCornerResponse(BaseModel):
    corner_number: int

    time_lost_seconds: float
    time_gained_seconds: float

    entry_time_loss_seconds: float
    exit_time_loss_seconds: float

    dominant_phase: str

    minimum_speed_delta_kmh: float
    apex_speed_delta_kmh: float
    exit_speed_delta_kmh: float

    issue_count: int


class RaceEngineerFocusResponse(BaseModel):
    rank: int

    focus_level: str

    corner_number: int

    recommendation_type: str
    priority: str
    phase: str

    title: str
    instruction: str
    rationale: str

    diagnostic_code: str

    corner_time_loss_seconds: float

    minimum_speed_delta_kmh: float
    apex_speed_delta_kmh: float
    exit_speed_delta_kmh: float


class RaceEngineerExplanationResponse(BaseModel):
    language: str
    text: str

    recommendation_count: int
    corner_count: int


class RaceEngineerAnalysisResponse(BaseModel):
    analysis_id: str | None

    reference_lap_number: int
    target_lap_number: int

    trend: str

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

    corners: list[
        RaceEngineerCornerResponse
    ]

    focuses: list[
        RaceEngineerFocusResponse
    ]

    explanation: (
        RaceEngineerExplanationResponse
        | None
    )

    @classmethod
    def from_pipeline_result(
        cls,
        result: RaceEngineerPipelineResult,
        *,
        analysis_id: str | None = None,
    ) -> "RaceEngineerAnalysisResponse":
        report = result.report

        corners = [
            RaceEngineerCornerResponse(
                corner_number=(
                    corner.corner_number
                ),
                time_lost_seconds=(
                    corner.time_lost_seconds
                ),
                time_gained_seconds=(
                    corner.time_gained_seconds
                ),
                entry_time_loss_seconds=(
                    corner
                    .entry_time_loss_seconds
                ),
                exit_time_loss_seconds=(
                    corner
                    .exit_time_loss_seconds
                ),
                dominant_phase=(
                    corner.dominant_phase.value
                ),
                minimum_speed_delta_kmh=(
                    corner
                    .minimum_speed_delta_kmh
                ),
                apex_speed_delta_kmh=(
                    corner
                    .apex_speed_delta_kmh
                ),
                exit_speed_delta_kmh=(
                    corner
                    .exit_speed_delta_kmh
                ),
                issue_count=(
                    corner.issue_count
                ),
            )
            for corner in report.corners
        ]

        focuses = [
            RaceEngineerFocusResponse(
                rank=focus.rank,
                focus_level=(
                    focus.focus_level.value
                ),
                corner_number=(
                    focus.corner_number
                ),
                recommendation_type=(
                    focus
                    .recommendation_type
                    .value
                ),
                priority=(
                    focus.priority.value
                ),
                phase=(
                    focus.phase.value
                ),
                title=focus.title,
                instruction=(
                    focus.instruction
                ),
                rationale=(
                    focus.rationale
                ),
                diagnostic_code=(
                    focus.diagnostic_code
                ),
                corner_time_loss_seconds=(
                    focus
                    .corner_time_loss_seconds
                ),
                minimum_speed_delta_kmh=(
                    focus
                    .minimum_speed_delta_kmh
                ),
                apex_speed_delta_kmh=(
                    focus
                    .apex_speed_delta_kmh
                ),
                exit_speed_delta_kmh=(
                    focus
                    .exit_speed_delta_kmh
                ),
            )
            for focus in report.focuses
        ]

        explanation = None

        if result.explanation is not None:
            explanation = (
                RaceEngineerExplanationResponse(
                    language=(
                        result.explanation.language
                    ),
                    text=(
                        result.explanation.text
                    ),
                    recommendation_count=(
                        result.explanation
                        .recommendation_count
                    ),
                    corner_count=(
                        result.explanation
                        .corner_count
                    ),
                )
            )

        return cls(
            analysis_id=analysis_id,
            reference_lap_number=(
                report.reference_lap_number
            ),
            target_lap_number=(
                report.target_lap_number
            ),
            trend=report.trend.value,
            total_time_lost_seconds=(
                report.total_time_lost_seconds
            ),
            total_time_gained_seconds=(
                report.total_time_gained_seconds
            ),
            net_time_delta_seconds=(
                report.net_time_delta_seconds
            ),
            corners_analyzed=(
                report.corners_analyzed
            ),
            corners_with_time_loss=(
                report.corners_with_time_loss
            ),
            corners_with_issues=(
                report.corners_with_issues
            ),
            recommendations_generated=(
                report.recommendations_generated
            ),
            recommendations_selected=(
                report.recommendations_selected
            ),
            recommendations_suppressed=(
                report
                .recommendations_suppressed
            ),
            primary_problem_corner=(
                report.primary_problem_corner
            ),
            corners=corners,
            focuses=focuses,
            explanation=explanation,
        )


class StoredRaceEngineerAnalysisResponse(
    BaseModel
):
    analysis_id: str

    session_id: str | None

    reference_lap_number: int
    target_lap_number: int

    trend: str

    total_time_lost_seconds: float
    total_time_gained_seconds: float
    net_time_delta_seconds: float

    primary_problem_corner: int | None

    recommendations_generated: int
    recommendations_selected: int
    recommendations_suppressed: int

    report: dict
    explanation: dict | None

    created_at: datetime

    @classmethod
    def from_record(
        cls,
        record: RaceEngineerAnalysisRecord,
    ) -> "StoredRaceEngineerAnalysisResponse":
        return cls(
            analysis_id=record.id,
            session_id=record.session_id,
            reference_lap_number=(
                record.reference_lap_number
            ),
            target_lap_number=(
                record.target_lap_number
            ),
            trend=record.trend,
            total_time_lost_seconds=(
                record
                .total_time_lost_seconds
            ),
            total_time_gained_seconds=(
                record
                .total_time_gained_seconds
            ),
            net_time_delta_seconds=(
                record.net_time_delta_seconds
            ),
            primary_problem_corner=(
                record.primary_problem_corner
            ),
            recommendations_generated=(
                record
                .recommendations_generated
            ),
            recommendations_selected=(
                record
                .recommendations_selected
            ),
            recommendations_suppressed=(
                record
                .recommendations_suppressed
            ),
            report=record.report_json,
            explanation=(
                record.explanation_json
            ),
            created_at=record.created_at,
        )