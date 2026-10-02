from dataclasses import dataclass
from enum import StrEnum

from ac_race_engineer.telemetry.assetto_corsa.trace_braking_comparison import (
    BrakingComparisonResult,
    BrakingZoneDelta,
)


class BrakingDiagnosticCode(StrEnum):
    BRAKING_TOO_EARLY = "BRAKING_TOO_EARLY"
    BRAKING_TOO_LATE = "BRAKING_TOO_LATE"
    OVER_SLOWING = "OVER_SLOWING"
    LATE_BRAKE_RELEASE = "LATE_BRAKE_RELEASE"
    EXCESSIVE_BRAKE_PRESSURE = (
        "EXCESSIVE_BRAKE_PRESSURE"
    )


class BrakingDiagnosticSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class BrakingDiagnosticEvidence:
    metric: str

    reference_value: float
    target_value: float
    delta_value: float

    unit: str


@dataclass(frozen=True)
class BrakingDiagnostic:
    code: BrakingDiagnosticCode
    severity: BrakingDiagnosticSeverity

    reference_zone_number: int
    target_zone_number: int

    center_progress: float

    time_loss_seconds: float

    summary: str

    evidence: tuple[
        BrakingDiagnosticEvidence,
        ...,
    ]


@dataclass(frozen=True)
class BrakingDiagnosticReport:
    reference_lap_number: int
    target_lap_number: int

    diagnostics: tuple[
        BrakingDiagnostic,
        ...,
    ]

    zones_analyzed: int
    zones_with_time_loss: int

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
    ) -> BrakingDiagnostic | None:
        if not self.diagnostics:
            return None

        return self.diagnostics[0]


class AssettoCorsaBrakingDiagnosticService:
    """
    Build deterministic braking diagnoses.

    Diagnostics are generated from measured differences
    between a reference lap and a target lap.

    No recommendation is created without measurable
    time loss in the braking zone.

    Delta convention:

        target - reference
    """

    def __init__(
        self,
        *,
        minimum_time_loss_seconds: float = 0.05,
        braking_point_threshold: float = 0.01,
        release_point_threshold: float = 0.01,
        minimum_speed_loss_kmh: float = 3.0,
        average_brake_increase_threshold: float = 0.08,
        peak_brake_increase_threshold: float = 0.08,
        duration_increase_threshold_seconds: float = 0.10,
        high_severity_time_loss_seconds: float = 0.40,
        medium_severity_time_loss_seconds: float = 0.15,
    ) -> None:
        if minimum_time_loss_seconds < 0.0:
            raise ValueError(
                "minimum_time_loss_seconds "
                "cannot be negative"
            )

        if braking_point_threshold <= 0.0:
            raise ValueError(
                "braking_point_threshold must "
                "be greater than 0"
            )

        if release_point_threshold <= 0.0:
            raise ValueError(
                "release_point_threshold must "
                "be greater than 0"
            )

        if minimum_speed_loss_kmh <= 0.0:
            raise ValueError(
                "minimum_speed_loss_kmh must "
                "be greater than 0"
            )

        if (
            average_brake_increase_threshold
            <= 0.0
        ):
            raise ValueError(
                "average_brake_increase_threshold "
                "must be greater than 0"
            )

        if (
            peak_brake_increase_threshold
            <= 0.0
        ):
            raise ValueError(
                "peak_brake_increase_threshold "
                "must be greater than 0"
            )

        if (
            duration_increase_threshold_seconds
            <= 0.0
        ):
            raise ValueError(
                "duration_increase_threshold_seconds "
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

        self.braking_point_threshold = (
            braking_point_threshold
        )

        self.release_point_threshold = (
            release_point_threshold
        )

        self.minimum_speed_loss_kmh = (
            minimum_speed_loss_kmh
        )

        self.average_brake_increase_threshold = (
            average_brake_increase_threshold
        )

        self.peak_brake_increase_threshold = (
            peak_brake_increase_threshold
        )

        self.duration_increase_threshold_seconds = (
            duration_increase_threshold_seconds
        )

        self.high_severity_time_loss_seconds = (
            high_severity_time_loss_seconds
        )

        self.medium_severity_time_loss_seconds = (
            medium_severity_time_loss_seconds
        )

    def _severity(
        self,
        time_loss_seconds: float,
    ) -> BrakingDiagnosticSeverity:
        if (
            time_loss_seconds
            >= self.high_severity_time_loss_seconds
        ):
            return (
                BrakingDiagnosticSeverity.HIGH
            )

        if (
            time_loss_seconds
            >= self.medium_severity_time_loss_seconds
        ):
            return (
                BrakingDiagnosticSeverity.MEDIUM
            )

        return BrakingDiagnosticSeverity.LOW

    @staticmethod
    def _evidence(
        *,
        metric: str,
        reference_value: float,
        target_value: float,
        unit: str,
    ) -> BrakingDiagnosticEvidence:
        return BrakingDiagnosticEvidence(
            metric=metric,
            reference_value=reference_value,
            target_value=target_value,
            delta_value=(
                target_value
                - reference_value
            ),
            unit=unit,
        )

    def _build_diagnostic(
        self,
        *,
        zone: BrakingZoneDelta,
        code: BrakingDiagnosticCode,
        summary: str,
        evidence: tuple[
            BrakingDiagnosticEvidence,
            ...,
        ],
    ) -> BrakingDiagnostic:
        time_loss = (
            zone.time_lost_seconds
            or 0.0
        )

        return BrakingDiagnostic(
            code=code,
            severity=self._severity(
                time_loss
            ),
            reference_zone_number=(
                zone.reference_zone_number
            ),
            target_zone_number=(
                zone.target_zone_number
            ),
            center_progress=(
                zone.reference_center_progress
            ),
            time_loss_seconds=(
                time_loss
            ),
            summary=summary,
            evidence=evidence,
        )

    def _diagnose_zone(
        self,
        zone: BrakingZoneDelta,
    ) -> tuple[
        BrakingDiagnostic,
        ...,
    ]:
        time_loss = (
            zone.time_lost_seconds
        )

        if time_loss is None:
            return ()

        if (
            time_loss
            < self.minimum_time_loss_seconds
        ):
            return ()

        diagnostics: list[
            BrakingDiagnostic
        ] = []

        if (
            zone.start_progress_delta
            <= -self.braking_point_threshold
        ):
            diagnostics.append(
                self._build_diagnostic(
                    zone=zone,
                    code=(
                        BrakingDiagnosticCode
                        .BRAKING_TOO_EARLY
                    ),
                    summary=(
                        "Target lap starts braking "
                        "earlier than the reference "
                        "in a time-losing zone."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "braking_start_progress"
                            ),
                            reference_value=(
                                zone
                                .reference_start_progress
                            ),
                            target_value=(
                                zone
                                .target_start_progress
                            ),
                            unit="normalized_progress",
                        ),
                    ),
                )
            )

        if (
            zone.start_progress_delta
            >= self.braking_point_threshold
        ):
            diagnostics.append(
                self._build_diagnostic(
                    zone=zone,
                    code=(
                        BrakingDiagnosticCode
                        .BRAKING_TOO_LATE
                    ),
                    summary=(
                        "Target lap starts braking "
                        "later than the reference "
                        "in a time-losing zone."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "braking_start_progress"
                            ),
                            reference_value=(
                                zone
                                .reference_start_progress
                            ),
                            target_value=(
                                zone
                                .target_start_progress
                            ),
                            unit="normalized_progress",
                        ),
                    ),
                )
            )

        if (
            zone.minimum_speed_delta_kmh
            <= -self.minimum_speed_loss_kmh
        ):
            diagnostics.append(
                self._build_diagnostic(
                    zone=zone,
                    code=(
                        BrakingDiagnosticCode
                        .OVER_SLOWING
                    ),
                    summary=(
                        "Target lap reaches a lower "
                        "minimum speed than the "
                        "reference in a time-losing "
                        "braking zone."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "minimum_speed"
                            ),
                            reference_value=(
                                zone
                                .reference_minimum_speed_kmh
                            ),
                            target_value=(
                                zone
                                .target_minimum_speed_kmh
                            ),
                            unit="km/h",
                        ),
                    ),
                )
            )

        if (
            zone.end_progress_delta
            >= self.release_point_threshold
            and zone.duration_delta_seconds
            >= (
                self
                .duration_increase_threshold_seconds
            )
        ):
            diagnostics.append(
                self._build_diagnostic(
                    zone=zone,
                    code=(
                        BrakingDiagnosticCode
                        .LATE_BRAKE_RELEASE
                    ),
                    summary=(
                        "Target lap releases the "
                        "brake later and keeps braking "
                        "for longer than the reference."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "braking_end_progress"
                            ),
                            reference_value=(
                                zone
                                .reference_end_progress
                            ),
                            target_value=(
                                zone
                                .target_end_progress
                            ),
                            unit="normalized_progress",
                        ),
                        self._evidence(
                            metric=(
                                "braking_duration"
                            ),
                            reference_value=(
                                zone
                                .reference_duration_seconds
                            ),
                            target_value=(
                                zone
                                .target_duration_seconds
                            ),
                            unit="s",
                        ),
                    ),
                )
            )

        excessive_average = (
            zone.average_brake_delta
            >= (
                self
                .average_brake_increase_threshold
            )
        )

        excessive_peak = (
            zone.peak_brake_delta
            >= (
                self
                .peak_brake_increase_threshold
            )
        )

        if (
            excessive_average
            or excessive_peak
        ):
            diagnostics.append(
                self._build_diagnostic(
                    zone=zone,
                    code=(
                        BrakingDiagnosticCode
                        .EXCESSIVE_BRAKE_PRESSURE
                    ),
                    summary=(
                        "Target lap applies more brake "
                        "pressure than the reference "
                        "in a time-losing zone."
                    ),
                    evidence=(
                        self._evidence(
                            metric=(
                                "average_brake"
                            ),
                            reference_value=(
                                zone
                                .reference_average_brake
                            ),
                            target_value=(
                                zone
                                .target_average_brake
                            ),
                            unit="ratio",
                        ),
                        self._evidence(
                            metric="peak_brake",
                            reference_value=(
                                zone
                                .reference_peak_brake
                            ),
                            target_value=(
                                zone
                                .target_peak_brake
                            ),
                            unit="ratio",
                        ),
                    ),
                )
            )

        return tuple(
            diagnostics
        )

    def analyze(
        self,
        comparison: BrakingComparisonResult,
    ) -> BrakingDiagnosticReport:
        diagnostics: list[
            BrakingDiagnostic
        ] = []

        zones_with_time_loss = 0

        total_time_loss = 0.0

        for zone in comparison.zones:
            time_loss = (
                zone.time_lost_seconds
            )

            if (
                time_loss is not None
                and time_loss > 0.0
            ):
                zones_with_time_loss += 1

                total_time_loss += (
                    time_loss
                )

            diagnostics.extend(
                self._diagnose_zone(
                    zone
                )
            )

        diagnostics.sort(
            key=lambda diagnostic: (
                -diagnostic.time_loss_seconds,
                diagnostic.center_progress,
                diagnostic.code.value,
            )
        )

        return BrakingDiagnosticReport(
            reference_lap_number=(
                comparison.reference_lap_number
            ),
            target_lap_number=(
                comparison.target_lap_number
            ),
            diagnostics=tuple(
                diagnostics
            ),
            zones_analyzed=len(
                comparison.zones
            ),
            zones_with_time_loss=(
                zones_with_time_loss
            ),
            total_time_loss_seconds=(
                total_time_loss
            ),
        )