from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry_comparison import (
    CornerEntryComparisonResult,
    CornerEntryDelta,
)


class CornerEntryDiagnosticCode(StrEnum):
    EARLY_TURN_IN = "EARLY_TURN_IN"
    LATE_TURN_IN = "LATE_TURN_IN"
    ENTRY_OVER_SLOWING = "ENTRY_OVER_SLOWING"
    EXCESSIVE_TRAIL_BRAKING = (
        "EXCESSIVE_TRAIL_BRAKING"
    )
    EXCESSIVE_STEERING = (
        "EXCESSIVE_STEERING"
    )
    POOR_APEX_SPEED = (
        "POOR_APEX_SPEED"
    )


class CornerEntryDiagnosticSeverity(
    StrEnum
):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class CornerEntryDiagnosticEvidence:
    metric: str

    reference_value: float
    target_value: float
    delta_value: float

    unit: str


@dataclass(frozen=True)
class CornerEntryDiagnostic:
    code: CornerEntryDiagnosticCode
    severity: CornerEntryDiagnosticSeverity

    reference_entry_number: int
    target_entry_number: int

    center_progress: float

    time_loss_seconds: float

    summary: str

    evidence: tuple[
        CornerEntryDiagnosticEvidence,
        ...,
    ]


@dataclass(frozen=True)
class CornerEntryDiagnosticReport:
    reference_lap_number: int
    target_lap_number: int

    diagnostics: tuple[
        CornerEntryDiagnostic,
        ...,
    ]

    entries_analyzed: int
    entries_with_time_loss: int

    total_time_loss_seconds: float

    @property
    def diagnostic_count(
        self,
    ) -> int:
        return len(
            self.diagnostics
        )

    @property
    def primary_diagnostic(
        self,
    ) -> CornerEntryDiagnostic | None:
        if not self.diagnostics:
            return None

        return self.diagnostics[0]


class AssettoCorsaCornerEntryDiagnosticService:
    """
    Build deterministic corner-entry diagnoses.

    Diagnoses are generated only from measurable
    differences between a reference lap and a target
    lap.

    A diagnostic is only emitted when the compared
    entry also contains meaningful time loss.

    Delta convention:

        target - reference
    """

    def __init__(
        self,
        *,
        minimum_time_loss_seconds: float = 0.05,
        turn_in_progress_threshold: float = 0.01,
        minimum_apex_speed_loss_kmh: float = 3.0,
        minimum_extra_speed_loss_kmh: float = 3.0,
        trail_brake_overlap_threshold_seconds: float = 0.15,
        brake_at_turn_in_threshold: float = 0.08,
        maximum_steering_threshold_deg: float = 3.0,
        average_steering_threshold_deg: float = 2.0,
        medium_severity_time_loss_seconds: float = 0.15,
        high_severity_time_loss_seconds: float = 0.40,
    ) -> None:
        if minimum_time_loss_seconds < 0.0:
            raise ValueError(
                "minimum_time_loss_seconds "
                "cannot be negative"
            )

        if (
            turn_in_progress_threshold
            <= 0.0
        ):
            raise ValueError(
                "turn_in_progress_threshold "
                "must be greater than 0"
            )

        if (
            minimum_apex_speed_loss_kmh
            <= 0.0
        ):
            raise ValueError(
                "minimum_apex_speed_loss_kmh "
                "must be greater than 0"
            )

        if (
            minimum_extra_speed_loss_kmh
            <= 0.0
        ):
            raise ValueError(
                "minimum_extra_speed_loss_kmh "
                "must be greater than 0"
            )

        if (
            trail_brake_overlap_threshold_seconds
            <= 0.0
        ):
            raise ValueError(
                "trail_brake_overlap_threshold_seconds "
                "must be greater than 0"
            )

        if (
            brake_at_turn_in_threshold
            <= 0.0
        ):
            raise ValueError(
                "brake_at_turn_in_threshold "
                "must be greater than 0"
            )

        if (
            maximum_steering_threshold_deg
            <= 0.0
        ):
            raise ValueError(
                "maximum_steering_threshold_deg "
                "must be greater than 0"
            )

        if (
            average_steering_threshold_deg
            <= 0.0
        ):
            raise ValueError(
                "average_steering_threshold_deg "
                "must be greater than 0"
            )

        if (
            medium_severity_time_loss_seconds
            <= 0.0
        ):
            raise ValueError(
                "medium_severity_time_loss_seconds "
                "must be greater than 0"
            )

        if (
            high_severity_time_loss_seconds
            <= medium_severity_time_loss_seconds
        ):
            raise ValueError(
                "high_severity_time_loss_seconds "
                "must be greater than "
                "medium_severity_time_loss_seconds"
            )

        self.minimum_time_loss_seconds = (
            minimum_time_loss_seconds
        )

        self.turn_in_progress_threshold = (
            turn_in_progress_threshold
        )

        self.minimum_apex_speed_loss_kmh = (
            minimum_apex_speed_loss_kmh
        )

        self.minimum_extra_speed_loss_kmh = (
            minimum_extra_speed_loss_kmh
        )

        self.trail_brake_overlap_threshold_seconds = (
            trail_brake_overlap_threshold_seconds
        )

        self.brake_at_turn_in_threshold = (
            brake_at_turn_in_threshold
        )

        self.maximum_steering_threshold_deg = (
            maximum_steering_threshold_deg
        )

        self.average_steering_threshold_deg = (
            average_steering_threshold_deg
        )

        self.medium_severity_time_loss_seconds = (
            medium_severity_time_loss_seconds
        )

        self.high_severity_time_loss_seconds = (
            high_severity_time_loss_seconds
        )

    def _severity(
        self,
        time_loss_seconds: float,
    ) -> CornerEntryDiagnosticSeverity:
        if (
            time_loss_seconds
            >= self.high_severity_time_loss_seconds
        ):
            return (
                CornerEntryDiagnosticSeverity.HIGH
            )

        if (
            time_loss_seconds
            >= self.medium_severity_time_loss_seconds
        ):
            return (
                CornerEntryDiagnosticSeverity.MEDIUM
            )

        return (
            CornerEntryDiagnosticSeverity.LOW
        )

    @staticmethod
    def _evidence(
        *,
        metric: str,
        reference_value: float,
        target_value: float,
        unit: str,
    ) -> CornerEntryDiagnosticEvidence:
        return CornerEntryDiagnosticEvidence(
            metric=metric,
            reference_value=(
                reference_value
            ),
            target_value=(
                target_value
            ),
            delta_value=(
                target_value
                - reference_value
            ),
            unit=unit,
        )

    def _build_diagnostic(
        self,
        *,
        entry: CornerEntryDelta,
        code: CornerEntryDiagnosticCode,
        summary: str,
        evidence: tuple[
            CornerEntryDiagnosticEvidence,
            ...,
        ],
    ) -> CornerEntryDiagnostic:
        time_loss = (
            entry.time_lost_seconds
            or 0.0
        )

        center_progress = (
            entry.reference_turn_in_progress
            + entry.reference_apex_progress
        ) / 2.0

        return CornerEntryDiagnostic(
            code=code,
            severity=self._severity(
                time_loss
            ),
            reference_entry_number=(
                entry.reference_entry_number
            ),
            target_entry_number=(
                entry.target_entry_number
            ),
            center_progress=(
                center_progress
            ),
            time_loss_seconds=(
                time_loss
            ),
            summary=summary,
            evidence=evidence,
        )

    def _diagnose_entry(
        self,
        entry: CornerEntryDelta,
    ) -> tuple[
        CornerEntryDiagnostic,
        ...,
    ]:
        time_loss = (
            entry.time_lost_seconds
        )

        if time_loss is None:
            return ()

        if (
            time_loss
            < self.minimum_time_loss_seconds
        ):
            return ()

        diagnostics: list[
            CornerEntryDiagnostic
        ] = []

        if (
            entry.turn_in_progress_delta
            <= -self.turn_in_progress_threshold
        ):
            diagnostics.append(
                self._build_diagnostic(
                    entry=entry,
                    code=(
                        CornerEntryDiagnosticCode
                        .EARLY_TURN_IN
                    ),
                    summary=(
                        "Target lap turns into the "
                        "corner earlier than the "
                        "reference in a time-losing "
                        "entry."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "turn_in_progress"
                            ),
                            reference_value=(
                                entry
                                .reference_turn_in_progress
                            ),
                            target_value=(
                                entry
                                .target_turn_in_progress
                            ),
                            unit=(
                                "normalized_progress"
                            ),
                        ),
                    ),
                )
            )

        if (
            entry.turn_in_progress_delta
            >= self.turn_in_progress_threshold
        ):
            diagnostics.append(
                self._build_diagnostic(
                    entry=entry,
                    code=(
                        CornerEntryDiagnosticCode
                        .LATE_TURN_IN
                    ),
                    summary=(
                        "Target lap turns into the "
                        "corner later than the "
                        "reference in a time-losing "
                        "entry."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "turn_in_progress"
                            ),
                            reference_value=(
                                entry
                                .reference_turn_in_progress
                            ),
                            target_value=(
                                entry
                                .target_turn_in_progress
                            ),
                            unit=(
                                "normalized_progress"
                            ),
                        ),
                    ),
                )
            )

        if (
            entry.speed_loss_delta_kmh
            >= self.minimum_extra_speed_loss_kmh
        ):
            diagnostics.append(
                self._build_diagnostic(
                    entry=entry,
                    code=(
                        CornerEntryDiagnosticCode
                        .ENTRY_OVER_SLOWING
                    ),
                    summary=(
                        "Target lap loses more speed "
                        "between turn-in and apex than "
                        "the reference."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "entry_speed_loss"
                            ),
                            reference_value=(
                                entry
                                .reference_speed_loss_kmh
                            ),
                            target_value=(
                                entry
                                .target_speed_loss_kmh
                            ),
                            unit="km/h",
                        ),
                    ),
                )
            )

        if (
            entry.apex_speed_delta_kmh
            <= -self.minimum_apex_speed_loss_kmh
        ):
            diagnostics.append(
                self._build_diagnostic(
                    entry=entry,
                    code=(
                        CornerEntryDiagnosticCode
                        .POOR_APEX_SPEED
                    ),
                    summary=(
                        "Target lap reaches a lower "
                        "apex speed than the reference "
                        "in a time-losing entry."
                    ),
                    evidence=(
                        self._evidence(
                            metric="apex_speed",
                            reference_value=(
                                entry
                                .reference_apex_speed_kmh
                            ),
                            target_value=(
                                entry
                                .target_apex_speed_kmh
                            ),
                            unit="km/h",
                        ),
                    ),
                )
            )

        excessive_overlap = (
            entry.brake_overlap_delta_seconds
            >= (
                self
                .trail_brake_overlap_threshold_seconds
            )
        )

        excessive_brake_at_turn_in = (
            entry.brake_at_turn_in_delta
            >= self.brake_at_turn_in_threshold
        )

        if (
            excessive_overlap
            and excessive_brake_at_turn_in
        ):
            diagnostics.append(
                self._build_diagnostic(
                    entry=entry,
                    code=(
                        CornerEntryDiagnosticCode
                        .EXCESSIVE_TRAIL_BRAKING
                    ),
                    summary=(
                        "Target lap carries more brake "
                        "into the corner and maintains "
                        "braking for longer after "
                        "turn-in."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "brake_overlap"
                            ),
                            reference_value=(
                                entry
                                .reference_brake_overlap_seconds
                            ),
                            target_value=(
                                entry
                                .target_brake_overlap_seconds
                            ),
                            unit="s",
                        ),
                        self._evidence(
                            metric=(
                                "brake_at_turn_in"
                            ),
                            reference_value=(
                                entry
                                .reference_brake_at_turn_in
                            ),
                            target_value=(
                                entry
                                .target_brake_at_turn_in
                            ),
                            unit="ratio",
                        ),
                    ),
                )
            )

        excessive_maximum_steering = (
            entry.maximum_abs_steering_delta_deg
            >= (
                self
                .maximum_steering_threshold_deg
            )
        )

        excessive_average_steering = (
            entry.average_abs_steering_delta_deg
            >= (
                self
                .average_steering_threshold_deg
            )
        )

        if (
            excessive_maximum_steering
            or excessive_average_steering
        ):
            diagnostics.append(
                self._build_diagnostic(
                    entry=entry,
                    code=(
                        CornerEntryDiagnosticCode
                        .EXCESSIVE_STEERING
                    ),
                    summary=(
                        "Target lap requires more "
                        "steering input than the "
                        "reference during the "
                        "corner-entry phase."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "maximum_abs_steering"
                            ),
                            reference_value=(
                                entry
                                .reference_maximum_abs_steering_deg
                            ),
                            target_value=(
                                entry
                                .target_maximum_abs_steering_deg
                            ),
                            unit="deg",
                        ),
                        self._evidence(
                            metric=(
                                "average_abs_steering"
                            ),
                            reference_value=(
                                entry
                                .reference_average_abs_steering_deg
                            ),
                            target_value=(
                                entry
                                .target_average_abs_steering_deg
                            ),
                            unit="deg",
                        ),
                    ),
                )
            )

        return tuple(
            diagnostics
        )

    def analyze(
        self,
        comparison: CornerEntryComparisonResult,
    ) -> CornerEntryDiagnosticReport:
        diagnostics: list[
            CornerEntryDiagnostic
        ] = []

        entries_with_time_loss = 0

        total_time_loss = 0.0

        for entry in comparison.entries:
            time_loss = (
                entry.time_lost_seconds
            )

            if (
                time_loss is not None
                and time_loss > 0.0
            ):
                entries_with_time_loss += 1

                total_time_loss += (
                    time_loss
                )

            diagnostics.extend(
                self._diagnose_entry(
                    entry
                )
            )

        diagnostics.sort(
            key=lambda diagnostic: (
                -diagnostic.time_loss_seconds,
                diagnostic.center_progress,
                diagnostic.code.value,
            )
        )

        return CornerEntryDiagnosticReport(
            reference_lap_number=(
                comparison.reference_lap_number
            ),
            target_lap_number=(
                comparison.target_lap_number
            ),
            diagnostics=tuple(
                diagnostics
            ),
            entries_analyzed=len(
                comparison.entries
            ),
            entries_with_time_loss=(
                entries_with_time_loss
            ),
            total_time_loss_seconds=(
                total_time_loss
            ),
        )