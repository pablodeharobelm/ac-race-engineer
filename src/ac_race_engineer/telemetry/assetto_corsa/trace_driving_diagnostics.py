from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.trace_braking_diagnostics import (
    BrakingDiagnostic,
    BrakingDiagnosticReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_diagnostics import (
    CornerEntryDiagnostic,
    CornerEntryDiagnosticReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_diagnostics import (
    CornerExitDiagnostic,
    CornerExitDiagnosticReport,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation_comparison import (
    TrackCornerSegmentDelta,
    TrackSegmentationComparisonResult,
)


class DrivingDiagnosticSource(StrEnum):
    BRAKING = "BRAKING"
    CORNER_ENTRY = "CORNER_ENTRY"
    CORNER_EXIT = "CORNER_EXIT"


class DrivingPhase(StrEnum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    BALANCED = "BALANCED"
    NONE = "NONE"


@dataclass(frozen=True)
class DrivingIssue:
    source: DrivingDiagnosticSource

    code: str
    severity: str

    summary: str

    center_progress: float
    diagnostic_time_loss_seconds: float


@dataclass(frozen=True)
class CornerDrivingDiagnosis:
    reference_corner_number: int
    target_corner_number: int

    start_progress: float
    apex_progress: float
    exit_progress: float

    time_lost_seconds: float
    time_gained_seconds: float

    entry_time_loss_seconds: float
    exit_time_loss_seconds: float

    dominant_phase: DrivingPhase

    minimum_speed_delta_kmh: float
    apex_speed_delta_kmh: float
    exit_speed_delta_kmh: float

    issues: tuple[
        DrivingIssue,
        ...,
    ]

    @property
    def issue_count(
        self,
    ) -> int:
        return len(
            self.issues
        )

    @property
    def has_issues(
        self,
    ) -> bool:
        return bool(
            self.issues
        )

    @property
    def primary_issue(
        self,
    ) -> DrivingIssue | None:
        if not self.issues:
            return None

        return self.issues[0]


@dataclass(frozen=True)
class RealDrivingDiagnosisReport:
    reference_lap_number: int
    target_lap_number: int

    corners: tuple[
        CornerDrivingDiagnosis,
        ...,
    ]

    unmatched_issue_count: int

    total_time_lost_seconds: float
    total_time_gained_seconds: float

    @property
    def diagnosed_corner_count(
        self,
    ) -> int:
        return len(
            self.corners
        )

    @property
    def corners_with_time_loss(
        self,
    ) -> int:
        return sum(
            1
            for corner in self.corners
            if corner.time_lost_seconds > 0.0
        )

    @property
    def corners_with_issues(
        self,
    ) -> int:
        return sum(
            1
            for corner in self.corners
            if corner.has_issues
        )

    @property
    def primary_problem_corner(
        self,
    ) -> CornerDrivingDiagnosis | None:
        losing = [
            corner
            for corner in self.corners
            if corner.time_lost_seconds > 0.0
        ]

        if not losing:
            return None

        return max(
            losing,
            key=lambda corner: (
                corner.time_lost_seconds
            ),
        )


class AssettoCorsaRealDrivingDiagnosticService:
    """
    Combine braking, corner-entry and corner-exit
    diagnostics into one driving report.

    TrackSegmentationComparisonResult is the timing
    authority.

    Individual diagnostic reports explain possible
    observable causes, but their time-loss values are
    not added together because multiple diagnostics can
    describe the same underlying loss.
    """

    def __init__(
        self,
        *,
        progress_tolerance: float = 0.02,
        balanced_phase_tolerance_seconds: float = 0.03,
    ) -> None:
        if not (
            0.0
            <= progress_tolerance
            <= 1.0
        ):
            raise ValueError(
                "progress_tolerance must "
                "be between 0 and 1"
            )

        if (
            balanced_phase_tolerance_seconds
            < 0.0
        ):
            raise ValueError(
                "balanced_phase_tolerance_seconds "
                "cannot be negative"
            )

        self.progress_tolerance = (
            progress_tolerance
        )

        self.balanced_phase_tolerance_seconds = (
            balanced_phase_tolerance_seconds
        )

    @staticmethod
    def _severity_priority(
        severity: str,
    ) -> int:
        priorities = {
            "HIGH": 0,
            "MEDIUM": 1,
            "LOW": 2,
        }

        return priorities.get(
            severity,
            3,
        )

    @staticmethod
    def _issue_from_braking(
        diagnostic: BrakingDiagnostic,
    ) -> DrivingIssue:
        return DrivingIssue(
            source=(
                DrivingDiagnosticSource.BRAKING
            ),
            code=diagnostic.code.value,
            severity=(
                diagnostic.severity.value
            ),
            summary=diagnostic.summary,
            center_progress=(
                diagnostic.center_progress
            ),
            diagnostic_time_loss_seconds=(
                diagnostic.time_loss_seconds
            ),
        )

    @staticmethod
    def _issue_from_entry(
        diagnostic: CornerEntryDiagnostic,
    ) -> DrivingIssue:
        return DrivingIssue(
            source=(
                DrivingDiagnosticSource
                .CORNER_ENTRY
            ),
            code=diagnostic.code.value,
            severity=(
                diagnostic.severity.value
            ),
            summary=diagnostic.summary,
            center_progress=(
                diagnostic.center_progress
            ),
            diagnostic_time_loss_seconds=(
                diagnostic.time_loss_seconds
            ),
        )

    @staticmethod
    def _issue_from_exit(
        diagnostic: CornerExitDiagnostic,
    ) -> DrivingIssue:
        return DrivingIssue(
            source=(
                DrivingDiagnosticSource
                .CORNER_EXIT
            ),
            code=diagnostic.code.value,
            severity=(
                diagnostic.severity.value
            ),
            summary=diagnostic.summary,
            center_progress=(
                diagnostic.center_progress
            ),
            diagnostic_time_loss_seconds=(
                diagnostic.time_loss_seconds
            ),
        )

    def _all_issues(
        self,
        *,
        braking_report: BrakingDiagnosticReport,
        entry_report: CornerEntryDiagnosticReport,
        exit_report: CornerExitDiagnosticReport,
    ) -> tuple[
        DrivingIssue,
        ...,
    ]:
        issues: list[
            DrivingIssue
        ] = []

        issues.extend(
            self._issue_from_braking(
                diagnostic
            )
            for diagnostic
            in braking_report.diagnostics
        )

        issues.extend(
            self._issue_from_entry(
                diagnostic
            )
            for diagnostic
            in entry_report.diagnostics
        )

        issues.extend(
            self._issue_from_exit(
                diagnostic
            )
            for diagnostic
            in exit_report.diagnostics
        )

        return tuple(
            issues
        )

    def _issue_belongs_to_corner(
        self,
        *,
        issue: DrivingIssue,
        corner: TrackCornerSegmentDelta,
    ) -> bool:
        minimum_progress = (
            corner
            .reference_braking_start_progress
            - self.progress_tolerance
        )

        maximum_progress = (
            corner
            .reference_exit_progress
            + self.progress_tolerance
        )

        return (
            minimum_progress
            <= issue.center_progress
            <= maximum_progress
        )

    def _dominant_phase(
        self,
        *,
        entry_loss: float,
        exit_loss: float,
    ) -> DrivingPhase:
        if (
            entry_loss <= 0.0
            and exit_loss <= 0.0
        ):
            return DrivingPhase.NONE

        difference = abs(
            entry_loss
            - exit_loss
        )

        if (
            difference
            <= (
                self
                .balanced_phase_tolerance_seconds
            )
        ):
            return DrivingPhase.BALANCED

        if entry_loss > exit_loss:
            return DrivingPhase.ENTRY

        return DrivingPhase.EXIT

    def _build_corner(
        self,
        *,
        corner: TrackCornerSegmentDelta,
        issues: tuple[
            DrivingIssue,
            ...,
        ],
    ) -> CornerDrivingDiagnosis:
        corner_issues = [
            issue
            for issue in issues
            if self._issue_belongs_to_corner(
                issue=issue,
                corner=corner,
            )
        ]

        corner_issues.sort(
            key=lambda issue: (
                self._severity_priority(
                    issue.severity
                ),
                -(
                    issue
                    .diagnostic_time_loss_seconds
                ),
                issue.center_progress,
                issue.code,
            )
        )

        time_lost = (
            corner.time_lost_seconds
            or 0.0
        )

        time_gained = (
            corner.time_gained_seconds
            or 0.0
        )

        entry_loss = (
            corner.entry_time_loss_seconds
            or 0.0
        )

        exit_loss = (
            corner.exit_time_loss_seconds
            or 0.0
        )

        return CornerDrivingDiagnosis(
            reference_corner_number=(
                corner.reference_corner_number
            ),
            target_corner_number=(
                corner.target_corner_number
            ),
            start_progress=(
                corner
                .reference_braking_start_progress
            ),
            apex_progress=(
                corner.reference_apex_progress
            ),
            exit_progress=(
                corner.reference_exit_progress
            ),
            time_lost_seconds=(
                time_lost
            ),
            time_gained_seconds=(
                time_gained
            ),
            entry_time_loss_seconds=(
                entry_loss
            ),
            exit_time_loss_seconds=(
                exit_loss
            ),
            dominant_phase=self._dominant_phase(
                entry_loss=entry_loss,
                exit_loss=exit_loss,
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
            issues=tuple(
                corner_issues
            ),
        )

    @staticmethod
    def _validate_laps(
        *,
        segmentation: TrackSegmentationComparisonResult,
        braking_report: BrakingDiagnosticReport,
        entry_report: CornerEntryDiagnosticReport,
        exit_report: CornerExitDiagnosticReport,
    ) -> None:
        expected = (
            segmentation.reference_lap_number,
            segmentation.target_lap_number,
        )

        reports = (
            (
                braking_report
                .reference_lap_number,
                braking_report
                .target_lap_number,
            ),
            (
                entry_report
                .reference_lap_number,
                entry_report
                .target_lap_number,
            ),
            (
                exit_report
                .reference_lap_number,
                exit_report
                .target_lap_number,
            ),
        )

        if any(
            value != expected
            for value in reports
        ):
            raise ValueError(
                "All diagnostic reports must "
                "reference the same laps"
            )

    def analyze(
        self,
        *,
        segmentation: TrackSegmentationComparisonResult,
        braking_report: BrakingDiagnosticReport,
        entry_report: CornerEntryDiagnosticReport,
        exit_report: CornerExitDiagnosticReport,
    ) -> RealDrivingDiagnosisReport:
        self._validate_laps(
            segmentation=segmentation,
            braking_report=braking_report,
            entry_report=entry_report,
            exit_report=exit_report,
        )

        issues = self._all_issues(
            braking_report=braking_report,
            entry_report=entry_report,
            exit_report=exit_report,
        )

        corners = tuple(
            self._build_corner(
                corner=corner,
                issues=issues,
            )
            for corner
            in segmentation.corners
        )

        matched_issue_ids = {
            id(issue)
            for corner in segmentation.corners
            for issue in issues
            if self._issue_belongs_to_corner(
                issue=issue,
                corner=corner,
            )
        }

        unmatched_issue_count = sum(
            1
            for issue in issues
            if id(issue)
            not in matched_issue_ids
        )

        ordered_corners = tuple(
            sorted(
                corners,
                key=lambda corner: (
                    -corner.time_lost_seconds,
                    corner.reference_corner_number,
                ),
            )
        )

        return RealDrivingDiagnosisReport(
            reference_lap_number=(
                segmentation
                .reference_lap_number
            ),
            target_lap_number=(
                segmentation
                .target_lap_number
            ),
            corners=ordered_corners,
            unmatched_issue_count=(
                unmatched_issue_count
            ),
            total_time_lost_seconds=(
                segmentation
                .total_time_lost_seconds
            ),
            total_time_gained_seconds=(
                segmentation
                .total_time_gained_seconds
            ),
        )