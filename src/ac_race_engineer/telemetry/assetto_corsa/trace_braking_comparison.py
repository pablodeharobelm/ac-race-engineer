from bisect import bisect_left
from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    BrakingZone,
)


@dataclass(frozen=True)
class BrakingZoneDelta:
    reference_zone_number: int
    target_zone_number: int

    reference_start_progress: float
    target_start_progress: float
    start_progress_delta: float

    reference_end_progress: float
    target_end_progress: float
    end_progress_delta: float

    reference_center_progress: float
    target_center_progress: float
    center_progress_delta: float

    reference_duration_seconds: float
    target_duration_seconds: float
    duration_delta_seconds: float

    reference_entry_speed_kmh: float
    target_entry_speed_kmh: float
    entry_speed_delta_kmh: float

    reference_minimum_speed_kmh: float
    target_minimum_speed_kmh: float
    minimum_speed_delta_kmh: float

    reference_exit_speed_kmh: float
    target_exit_speed_kmh: float
    exit_speed_delta_kmh: float

    reference_peak_brake: float
    target_peak_brake: float
    peak_brake_delta: float

    reference_average_brake: float
    target_average_brake: float
    average_brake_delta: float

    time_delta_at_start_seconds: float | None
    time_delta_at_end_seconds: float | None
    time_delta_change_seconds: float | None

    overlap_progress: float
    overlap_ratio: float

    @property
    def target_brakes_earlier(
        self,
    ) -> bool:
        return (
            self.start_progress_delta
            < 0.0
        )

    @property
    def target_brakes_later(
        self,
    ) -> bool:
        return (
            self.start_progress_delta
            > 0.0
        )

    @property
    def target_releases_brake_earlier(
        self,
    ) -> bool:
        return (
            self.end_progress_delta
            < 0.0
        )

    @property
    def target_releases_brake_later(
        self,
    ) -> bool:
        return (
            self.end_progress_delta
            > 0.0
        )

    @property
    def time_lost_seconds(
        self,
    ) -> float | None:
        if (
            self.time_delta_change_seconds
            is None
        ):
            return None

        return max(
            0.0,
            self.time_delta_change_seconds,
        )

    @property
    def time_gained_seconds(
        self,
    ) -> float | None:
        if (
            self.time_delta_change_seconds
            is None
        ):
            return None

        return max(
            0.0,
            -self.time_delta_change_seconds,
        )


@dataclass(frozen=True)
class BrakingComparisonResult:
    reference_lap_number: int
    target_lap_number: int

    zones: tuple[
        BrakingZoneDelta,
        ...,
    ]

    unmatched_reference_zones: tuple[
        int,
        ...,
    ]

    unmatched_target_zones: tuple[
        int,
        ...,
    ]

    @property
    def matched_zone_count(
        self,
    ) -> int:
        return len(
            self.zones
        )

    @property
    def total_time_lost_seconds(
        self,
    ) -> float:
        return sum(
            zone.time_lost_seconds
            or 0.0
            for zone in self.zones
        )

    @property
    def total_time_gained_seconds(
        self,
    ) -> float:
        return sum(
            zone.time_gained_seconds
            or 0.0
            for zone in self.zones
        )


class AssettoCorsaBrakingComparisonService:
    """
    Compare braking zones between two aligned laps.

    Zone matching is based on track position,
    not zone number.

    Delta convention:

        target - reference

    Therefore:

        start_progress_delta < 0
            target started braking earlier

        start_progress_delta > 0
            target started braking later

        minimum_speed_delta_kmh < 0
            target reached a lower minimum speed

        time_delta_change_seconds > 0
            target lost time through the zone

        time_delta_change_seconds < 0
            target gained time through the zone
    """

    def __init__(
        self,
        *,
        maximum_center_distance: float = 0.05,
        minimum_overlap_ratio: float = 0.20,
    ) -> None:
        if not (
            0.0
            < maximum_center_distance
            <= 1.0
        ):
            raise ValueError(
                "maximum_center_distance must "
                "be greater than 0 and at most 1"
            )

        if not (
            0.0
            <= minimum_overlap_ratio
            <= 1.0
        ):
            raise ValueError(
                "minimum_overlap_ratio must "
                "be between 0 and 1"
            )

        self.maximum_center_distance = (
            maximum_center_distance
        )

        self.minimum_overlap_ratio = (
            minimum_overlap_ratio
        )

    @staticmethod
    def _overlap(
        reference: BrakingZone,
        target: BrakingZone,
    ) -> float:
        start = max(
            reference.start_progress,
            target.start_progress,
        )

        end = min(
            reference.end_progress,
            target.end_progress,
        )

        return max(
            0.0,
            end - start,
        )

    @classmethod
    def _overlap_ratio(
        cls,
        reference: BrakingZone,
        target: BrakingZone,
    ) -> float:
        overlap = cls._overlap(
            reference,
            target,
        )

        if overlap <= 0.0:
            return 0.0

        reference_span = max(
            0.0,
            reference.progress_span,
        )

        target_span = max(
            0.0,
            target.progress_span,
        )

        smallest_span = min(
            reference_span,
            target_span,
        )

        if smallest_span <= 0.0:
            return 0.0

        return (
            overlap
            / smallest_span
        )

    def _zones_can_match(
        self,
        reference: BrakingZone,
        target: BrakingZone,
    ) -> bool:
        overlap_ratio = (
            self._overlap_ratio(
                reference,
                target,
            )
        )

        center_distance = abs(
            target.center_progress
            - reference.center_progress
        )

        return (
            overlap_ratio
            >= self.minimum_overlap_ratio
            or center_distance
            <= self.maximum_center_distance
        )

    def _match_score(
        self,
        *,
        reference: BrakingZone,
        target: BrakingZone,
    ) -> tuple[
        int,
        float,
        float,
    ]:
        overlap_ratio = (
            self._overlap_ratio(
                reference,
                target,
            )
        )

        center_distance = abs(
            target.center_progress
            - reference.center_progress
        )

        has_overlap = (
            overlap_ratio > 0.0
        )

        return (
            0
            if has_overlap
            else 1,
            center_distance,
            -overlap_ratio,
        )

    def _select_best_target(
        self,
        *,
        reference: BrakingZone,
        candidates: list[
            BrakingZone
        ],
    ) -> BrakingZone:
        scored_candidates = [
            (
                self._match_score(
                    reference=reference,
                    target=target,
                ),
                target,
            )
            for target in candidates
        ]

        return min(
            scored_candidates,
            key=lambda item: item[0],
        )[1]

    def _match_zones(
        self,
        reference_zones: tuple[
            BrakingZone,
            ...,
        ],
        target_zones: tuple[
            BrakingZone,
            ...,
        ],
    ) -> tuple[
        tuple[
            BrakingZone,
            BrakingZone,
        ],
        ...,
    ]:
        available_targets = list(
            target_zones
        )

        matches: list[
            tuple[
                BrakingZone,
                BrakingZone,
            ]
        ] = []

        ordered_reference = sorted(
            reference_zones,
            key=lambda zone: (
                zone.center_progress
            ),
        )

        for reference in ordered_reference:
            candidates = [
                target
                for target
                in available_targets
                if self._zones_can_match(
                    reference,
                    target,
                )
            ]

            if not candidates:
                continue

            target = (
                self._select_best_target(
                    reference=reference,
                    candidates=candidates,
                )
            )

            matches.append(
                (
                    reference,
                    target,
                )
            )

            available_targets.remove(
                target
            )

        return tuple(
            matches
        )

    @staticmethod
    def _interpolate_time_delta(
        points: tuple[
            AlignedTracePoint,
            ...,
        ],
        progress: float,
    ) -> float | None:
        if not points:
            return None

        if (
            progress
            < points[0].progress
            or progress
            > points[-1].progress
        ):
            return None

        positions = tuple(
            point.progress
            for point in points
        )

        index = bisect_left(
            positions,
            progress,
        )

        if index == 0:
            return (
                points[0]
                .time_delta_seconds
            )

        if index >= len(
            points
        ):
            return (
                points[-1]
                .time_delta_seconds
            )

        right = points[
            index
        ]

        if (
            right.progress
            == progress
        ):
            return (
                right.time_delta_seconds
            )

        left = points[
            index - 1
        ]

        distance = (
            right.progress
            - left.progress
        )

        if distance <= 0.0:
            return (
                right.time_delta_seconds
            )

        ratio = (
            progress
            - left.progress
        ) / distance

        return (
            left.time_delta_seconds
            + (
                right.time_delta_seconds
                - left.time_delta_seconds
            )
            * ratio
        )

    def _build_delta(
        self,
        *,
        reference: BrakingZone,
        target: BrakingZone,
        trace_comparison: LapTraceComparison,
    ) -> BrakingZoneDelta:
        start_time_delta = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.start_progress,
            )
        )

        end_time_delta = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.end_progress,
            )
        )

        time_delta_change: (
            float | None
        )

        if (
            start_time_delta is None
            or end_time_delta is None
        ):
            time_delta_change = None

        else:
            time_delta_change = (
                end_time_delta
                - start_time_delta
            )

        overlap_progress = (
            self._overlap(
                reference,
                target,
            )
        )

        overlap_ratio = (
            self._overlap_ratio(
                reference,
                target,
            )
        )

        return BrakingZoneDelta(
            reference_zone_number=(
                reference.zone_number
            ),
            target_zone_number=(
                target.zone_number
            ),
            reference_start_progress=(
                reference.start_progress
            ),
            target_start_progress=(
                target.start_progress
            ),
            start_progress_delta=(
                target.start_progress
                - reference.start_progress
            ),
            reference_end_progress=(
                reference.end_progress
            ),
            target_end_progress=(
                target.end_progress
            ),
            end_progress_delta=(
                target.end_progress
                - reference.end_progress
            ),
            reference_center_progress=(
                reference.center_progress
            ),
            target_center_progress=(
                target.center_progress
            ),
            center_progress_delta=(
                target.center_progress
                - reference.center_progress
            ),
            reference_duration_seconds=(
                reference.duration_seconds
            ),
            target_duration_seconds=(
                target.duration_seconds
            ),
            duration_delta_seconds=(
                target.duration_seconds
                - reference.duration_seconds
            ),
            reference_entry_speed_kmh=(
                reference.entry_speed_kmh
            ),
            target_entry_speed_kmh=(
                target.entry_speed_kmh
            ),
            entry_speed_delta_kmh=(
                target.entry_speed_kmh
                - reference.entry_speed_kmh
            ),
            reference_minimum_speed_kmh=(
                reference.minimum_speed_kmh
            ),
            target_minimum_speed_kmh=(
                target.minimum_speed_kmh
            ),
            minimum_speed_delta_kmh=(
                target.minimum_speed_kmh
                - reference.minimum_speed_kmh
            ),
            reference_exit_speed_kmh=(
                reference.exit_speed_kmh
            ),
            target_exit_speed_kmh=(
                target.exit_speed_kmh
            ),
            exit_speed_delta_kmh=(
                target.exit_speed_kmh
                - reference.exit_speed_kmh
            ),
            reference_peak_brake=(
                reference.peak_brake
            ),
            target_peak_brake=(
                target.peak_brake
            ),
            peak_brake_delta=(
                target.peak_brake
                - reference.peak_brake
            ),
            reference_average_brake=(
                reference.average_brake
            ),
            target_average_brake=(
                target.average_brake
            ),
            average_brake_delta=(
                target.average_brake
                - reference.average_brake
            ),
            time_delta_at_start_seconds=(
                start_time_delta
            ),
            time_delta_at_end_seconds=(
                end_time_delta
            ),
            time_delta_change_seconds=(
                time_delta_change
            ),
            overlap_progress=(
                overlap_progress
            ),
            overlap_ratio=(
                overlap_ratio
            ),
        )

    def compare(
        self,
        *,
        reference_zones: tuple[
            BrakingZone,
            ...,
        ],
        target_zones: tuple[
            BrakingZone,
            ...,
        ],
        trace_comparison: LapTraceComparison,
    ) -> BrakingComparisonResult:
        matches = self._match_zones(
            reference_zones,
            target_zones,
        )

        matched_reference_numbers = {
            reference.zone_number
            for reference, _
            in matches
        }

        matched_target_numbers = {
            target.zone_number
            for _, target
            in matches
        }

        zones = tuple(
            self._build_delta(
                reference=reference,
                target=target,
                trace_comparison=(
                    trace_comparison
                ),
            )
            for reference, target
            in matches
        )

        unmatched_reference = tuple(
            zone.zone_number
            for zone in reference_zones
            if (
                zone.zone_number
                not in matched_reference_numbers
            )
        )

        unmatched_target = tuple(
            zone.zone_number
            for zone in target_zones
            if (
                zone.zone_number
                not in matched_target_numbers
            )
        )

        return BrakingComparisonResult(
            reference_lap_number=(
                trace_comparison
                .reference_lap_number
            ),
            target_lap_number=(
                trace_comparison
                .target_lap_number
            ),
            zones=zones,
            unmatched_reference_zones=(
                unmatched_reference
            ),
            unmatched_target_zones=(
                unmatched_target
            ),
        )