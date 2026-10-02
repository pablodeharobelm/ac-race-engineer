from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit_comparison import (
    CornerExitComparisonResult,
    CornerExitDelta,
)


class CornerExitDiagnosticCode(StrEnum):
    LATE_THROTTLE_APPLICATION = (
        "LATE_THROTTLE_APPLICATION"
    )
    POOR_EXIT_SPEED = "POOR_EXIT_SPEED"
    LOW_EXIT_THROTTLE = "LOW_EXIT_THROTTLE"
    SLOW_STEERING_UNWIND = (
        "SLOW_STEERING_UNWIND"
    )


class CornerExitDiagnosticSeverity(
    StrEnum
):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class CornerExitDiagnosticEvidence:
    metric: str
    reference_value: float
    target_value: float
    delta_value: float
    unit: str


@dataclass(frozen=True)
class CornerExitDiagnostic:
    code: CornerExitDiagnosticCode
    severity: CornerExitDiagnosticSeverity

    reference_exit_number: int
    target_exit_number: int

    center_progress: float
    time_loss_seconds: float

    summary: str

    evidence: tuple[
        CornerExitDiagnosticEvidence,
        ...,
    ]


@dataclass(frozen=True)
class CornerExitDiagnosticReport:
    reference_lap_number: int
    target_lap_number: int

    diagnostics: tuple[
        CornerExitDiagnostic,
        ...,
    ]

    exits_analyzed: int
    exits_with_time_loss: int
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
    ) -> CornerExitDiagnostic | None:
        if not self.diagnostics:
            return None

        return self.diagnostics[0]


class AssettoCorsaCornerExitDiagnosticService:
    def __init__(
        self,
        *,
        minimum_time_loss_seconds: float = 0.05,
        throttle_progress_threshold: float = 0.01,
        time_to_throttle_threshold_seconds: float = 0.15,
        exit_speed_loss_threshold_kmh: float = 3.0,
        exit_throttle_loss_threshold: float = 0.10,
        steering_at_exit_threshold_deg: float = 3.0,
        steering_unwind_loss_threshold_deg: float = 3.0,
        medium_severity_time_loss_seconds: float = 0.15,
        high_severity_time_loss_seconds: float = 0.40,
    ) -> None:
        if minimum_time_loss_seconds < 0.0:
            raise ValueError(
                "minimum_time_loss_seconds "
                "cannot be negative"
            )

        if throttle_progress_threshold <= 0.0:
            raise ValueError(
                "throttle_progress_threshold "
                "must be greater than 0"
            )

        if (
            time_to_throttle_threshold_seconds
            <= 0.0
        ):
            raise ValueError(
                "time_to_throttle_threshold_seconds "
                "must be greater than 0"
            )

        if (
            exit_speed_loss_threshold_kmh
            <= 0.0
        ):
            raise ValueError(
                "exit_speed_loss_threshold_kmh "
                "must be greater than 0"
            )

        if (
            exit_throttle_loss_threshold
            <= 0.0
        ):
            raise ValueError(
                "exit_throttle_loss_threshold "
                "must be greater than 0"
            )

        if (
            steering_at_exit_threshold_deg
            <= 0.0
        ):
            raise ValueError(
                "steering_at_exit_threshold_deg "
                "must be greater than 0"
            )

        if (
            steering_unwind_loss_threshold_deg
            <= 0.0
        ):
            raise ValueError(
                "steering_unwind_loss_threshold_deg "
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

        self.throttle_progress_threshold = (
            throttle_progress_threshold
        )

        self.time_to_throttle_threshold_seconds = (
            time_to_throttle_threshold_seconds
        )

        self.exit_speed_loss_threshold_kmh = (
            exit_speed_loss_threshold_kmh
        )

        self.exit_throttle_loss_threshold = (
            exit_throttle_loss_threshold
        )

        self.steering_at_exit_threshold_deg = (
            steering_at_exit_threshold_deg
        )

        self.steering_unwind_loss_threshold_deg = (
            steering_unwind_loss_threshold_deg
        )

        self.medium_severity_time_loss_seconds = (
            medium_severity_time_loss_seconds
        )

        self.high_severity_time_loss_seconds = (
            high_severity_time_loss_seconds
        )

    def _severity(
        self,
        time_loss: float,
    ) -> CornerExitDiagnosticSeverity:
        if (
            time_loss
            >= self.high_severity_time_loss_seconds
        ):
            return (
                CornerExitDiagnosticSeverity.HIGH
            )

        if (
            time_loss
            >= self.medium_severity_time_loss_seconds
        ):
            return (
                CornerExitDiagnosticSeverity.MEDIUM
            )

        return CornerExitDiagnosticSeverity.LOW

    @staticmethod
    def _evidence(
        *,
        metric: str,
        reference_value: float,
        target_value: float,
        unit: str,
    ) -> CornerExitDiagnosticEvidence:
        return CornerExitDiagnosticEvidence(
            metric=metric,
            reference_value=reference_value,
            target_value=target_value,
            delta_value=(
                target_value
                - reference_value
            ),
            unit=unit,
        )

    def _diagnostic(
        self,
        *,
        item: CornerExitDelta,
        code: CornerExitDiagnosticCode,
        summary: str,
        evidence: tuple[
            CornerExitDiagnosticEvidence,
            ...,
        ],
    ) -> CornerExitDiagnostic:
        time_loss = (
            item.time_lost_seconds
            or 0.0
        )

        center_progress = (
            item.reference_apex_progress
            + item.reference_exit_progress
        ) / 2.0

        return CornerExitDiagnostic(
            code=code,
            severity=self._severity(
                time_loss
            ),
            reference_exit_number=(
                item.reference_exit_number
            ),
            target_exit_number=(
                item.target_exit_number
            ),
            center_progress=center_progress,
            time_loss_seconds=time_loss,
            summary=summary,
            evidence=evidence,
        )

    def _analyze_exit(
        self,
        item: CornerExitDelta,
    ) -> tuple[
        CornerExitDiagnostic,
        ...,
    ]:
        time_loss = item.time_lost_seconds

        if time_loss is None:
            return ()

        if (
            time_loss
            < self.minimum_time_loss_seconds
        ):
            return ()

        diagnostics: list[
            CornerExitDiagnostic
        ] = []

        late_by_progress = (
            item
            .throttle_application_progress_delta
            >= self.throttle_progress_threshold
        )

        late_by_time = (
            item.time_to_throttle_delta_seconds
            >= (
                self
                .time_to_throttle_threshold_seconds
            )
        )

        if (
            late_by_progress
            or late_by_time
        ):
            diagnostics.append(
                self._diagnostic(
                    item=item,
                    code=(
                        CornerExitDiagnosticCode
                        .LATE_THROTTLE_APPLICATION
                    ),
                    summary=(
                        "Target lap applies meaningful "
                        "throttle later than the "
                        "reference during corner exit."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "throttle_application_progress"
                            ),
                            reference_value=(
                                item
                                .reference_throttle_application_progress
                            ),
                            target_value=(
                                item
                                .target_throttle_application_progress
                            ),
                            unit=(
                                "normalized_progress"
                            ),
                        ),
                        self._evidence(
                            metric="time_to_throttle",
                            reference_value=(
                                item
                                .reference_time_to_throttle_seconds
                            ),
                            target_value=(
                                item
                                .target_time_to_throttle_seconds
                            ),
                            unit="s",
                        ),
                    ),
                )
            )

        if (
            item.exit_speed_delta_kmh
            <= -self.exit_speed_loss_threshold_kmh
        ):
            diagnostics.append(
                self._diagnostic(
                    item=item,
                    code=(
                        CornerExitDiagnosticCode
                        .POOR_EXIT_SPEED
                    ),
                    summary=(
                        "Target lap leaves the corner "
                        "with less speed than the "
                        "reference."
                    ),
                    evidence=(
                        self._evidence(
                            metric="exit_speed",
                            reference_value=(
                                item
                                .reference_exit_speed_kmh
                            ),
                            target_value=(
                                item
                                .target_exit_speed_kmh
                            ),
                            unit="km/h",
                        ),
                    ),
                )
            )

        if (
            item.throttle_at_exit_delta
            <= -self.exit_throttle_loss_threshold
        ):
            diagnostics.append(
                self._diagnostic(
                    item=item,
                    code=(
                        CornerExitDiagnosticCode
                        .LOW_EXIT_THROTTLE
                    ),
                    summary=(
                        "Target lap uses less throttle "
                        "than the reference at corner "
                        "exit."
                    ),
                    evidence=(
                        self._evidence(
                            metric="exit_throttle",
                            reference_value=(
                                item
                                .reference_throttle_at_exit
                            ),
                            target_value=(
                                item
                                .target_throttle_at_exit
                            ),
                            unit="ratio",
                        ),
                    ),
                )
            )

        more_steering_at_exit = (
            item.abs_steering_at_exit_delta_deg
            >= self.steering_at_exit_threshold_deg
        )

        less_steering_unwind = (
            item.steering_unwind_delta_deg
            <= -(
                self
                .steering_unwind_loss_threshold_deg
            )
        )

        if (
            more_steering_at_exit
            or less_steering_unwind
        ):
            diagnostics.append(
                self._diagnostic(
                    item=item,
                    code=(
                        CornerExitDiagnosticCode
                        .SLOW_STEERING_UNWIND
                    ),
                    summary=(
                        "Target lap keeps more steering "
                        "angle through the exit than "
                        "the reference."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "abs_steering_at_exit"
                            ),
                            reference_value=(
                                item
                                .reference_abs_steering_at_exit_deg
                            ),
                            target_value=(
                                item
                                .target_abs_steering_at_exit_deg
                            ),
                            unit="deg",
                        ),
                        self._evidence(
                            metric="steering_unwind",
                            reference_value=(
                                item
                                .reference_steering_unwind_deg
                            ),
                            target_value=(
                                item
                                .target_steering_unwind_deg
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
        comparison: CornerExitComparisonResult,
    ) -> CornerExitDiagnosticReport:
        diagnostics: list[
            CornerExitDiagnostic
        ] = []

        exits_with_loss = 0
        total_loss = 0.0

        for item in comparison.exits:
            time_loss = (
                item.time_lost_seconds
            )

            if (
                time_loss is not None
                and time_loss > 0.0
            ):
                exits_with_loss += 1
                total_loss += time_loss

            diagnostics.extend(
                self._analyze_exit(
                    item
                )
            )

        diagnostics.sort(
            key=lambda item: (
                -item.time_loss_seconds,
                item.center_progress,
                item.code.value,
            )
        )

        return CornerExitDiagnosticReport(
            reference_lap_number=(
                comparison.reference_lap_number
            ),
            target_lap_number=(
                comparison.target_lap_number
            ),
            diagnostics=tuple(
                diagnostics
            ),
            exits_analyzed=len(
                comparison.exits
            ),
            exits_with_time_loss=(
                exits_with_loss
            ),
            total_time_loss_seconds=(
                total_loss
            ),
        )