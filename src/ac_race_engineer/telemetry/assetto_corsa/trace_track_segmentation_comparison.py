from bisect import bisect_left
from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_track_segmentation import (
    TrackCornerSegment,
)


@dataclass(frozen=True)
class TrackCornerSegmentDelta:
    reference_corner_number: int
    target_corner_number: int

    reference_braking_start_progress: float
    target_braking_start_progress: float
    braking_start_progress_delta: float

    reference_turn_in_progress: float
    target_turn_in_progress: float
    turn_in_progress_delta: float

    reference_apex_progress: float
    target_apex_progress: float
    apex_progress_delta: float

    reference_throttle_application_progress: float
    target_throttle_application_progress: float
    throttle_application_progress_delta: float

    reference_exit_progress: float
    target_exit_progress: float
    exit_progress_delta: float

    reference_minimum_speed_kmh: float
    target_minimum_speed_kmh: float
    minimum_speed_delta_kmh: float

    reference_apex_speed_kmh: float
    target_apex_speed_kmh: float
    apex_speed_delta_kmh: float

    reference_exit_speed_kmh: float
    target_exit_speed_kmh: float
    exit_speed_delta_kmh: float

    reference_total_duration_seconds: float
    target_total_duration_seconds: float
    total_duration_delta_seconds: float

    time_delta_at_start_seconds: float | None
    time_delta_at_apex_seconds: float | None
    time_delta_at_exit_seconds: float | None

    time_delta_to_apex_change_seconds: float | None
    time_delta_exit_change_seconds: float | None
    time_delta_total_change_seconds: float | None

    @property
    def time_lost_seconds(
        self,
    ) -> float | None:
        if (
            self.time_delta_total_change_seconds
            is None
        ):
            return None

        return max(
            0.0,
            self.time_delta_total_change_seconds,
        )

    @property
    def time_gained_seconds(
        self,
    ) -> float | None:
        if (
            self.time_delta_total_change_seconds
            is None
        ):
            return None

        return max(
            0.0,
            -self.time_delta_total_change_seconds,
        )

    @property
    def entry_time_loss_seconds(
        self,
    ) -> float | None:
        if (
            self.time_delta_to_apex_change_seconds
            is None
        ):
            return None

        return max(
            0.0,
            self.time_delta_to_apex_change_seconds,
        )

    @property
    def exit_time_loss_seconds(
        self,
    ) -> float | None:
        if (
            self.time_delta_exit_change_seconds
            is None
        ):
            return None

        return max(
            0.0,
            self.time_delta_exit_change_seconds,
        )


@dataclass(frozen=True)
class TrackSegmentationComparisonResult:
    reference_lap_number: int
    target_lap_number: int

    corners: tuple[
        TrackCornerSegmentDelta,
        ...,
    ]

    unmatched_reference_corners: tuple[
        int,
        ...,
    ]

    unmatched_target_corners: tuple[
        int,
        ...,
    ]

    @property
    def matched_corner_count(
        self,
    ) -> int:
        return len(
            self.corners
        )

    @property
    def total_time_lost_seconds(
        self,
    ) -> float:
        return sum(
            corner.time_lost_seconds
            or 0.0
            for corner in self.corners
        )

    @property
    def total_time_gained_seconds(
        self,
    ) -> float:
        return sum(
            corner.time_gained_seconds
            or 0.0
            for corner in self.corners
        )


class AssettoCorsaTrackSegmentationComparisonService:
    """
    Compare complete logical corners between two laps.

    Matching is based on apex position.

    The comparison also splits accumulated delta into:

        braking start -> apex
        apex -> exit
        braking start -> exit
    """

    def __init__(
        self,
        *,
        maximum_apex_distance: float = 0.05,
    ) -> None:
        if not (
            0.0
            < maximum_apex_distance
            <= 1.0
        ):
            raise ValueError(
                "maximum_apex_distance must "
                "be greater than 0 and at most 1"
            )

        self.maximum_apex_distance = (
            maximum_apex_distance
        )

    def _can_match(
        self,
        reference: TrackCornerSegment,
        target: TrackCornerSegment,
    ) -> bool:
        return (
            abs(
                target.apex_progress
                - reference.apex_progress
            )
            <= self.maximum_apex_distance
        )

    @staticmethod
    def _match_score(
        *,
        reference: TrackCornerSegment,
        target: TrackCornerSegment,
    ) -> float:
        return abs(
            target.apex_progress
            - reference.apex_progress
        )

    def _select_target(
        self,
        *,
        reference: TrackCornerSegment,
        candidates: list[
            TrackCornerSegment
        ],
    ) -> TrackCornerSegment:
        scored = [
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
            scored,
            key=lambda item: item[0],
        )[1]

    def _match_corners(
        self,
        *,
        reference_corners: tuple[
            TrackCornerSegment,
            ...,
        ],
        target_corners: tuple[
            TrackCornerSegment,
            ...,
        ],
    ) -> tuple[
        tuple[
            TrackCornerSegment,
            TrackCornerSegment,
        ],
        ...,
    ]:
        available_targets = list(
            target_corners
        )

        matches: list[
            tuple[
                TrackCornerSegment,
                TrackCornerSegment,
            ]
        ] = []

        ordered_reference = sorted(
            reference_corners,
            key=lambda corner: (
                corner.apex_progress
            ),
        )

        for reference in ordered_reference:
            candidates = [
                target
                for target
                in available_targets
                if self._can_match(
                    reference,
                    target,
                )
            ]

            if not candidates:
                continue

            target = self._select_target(
                reference=reference,
                candidates=candidates,
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

        if right.progress == progress:
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
        reference: TrackCornerSegment,
        target: TrackCornerSegment,
        trace_comparison: LapTraceComparison,
    ) -> TrackCornerSegmentDelta:
        time_at_start = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.start_progress,
            )
        )

        time_at_apex = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.apex_progress,
            )
        )

        time_at_exit = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.exit_progress,
            )
        )

        if (
            time_at_start is None
            or time_at_apex is None
        ):
            time_to_apex_change = None
        else:
            time_to_apex_change = (
                time_at_apex
                - time_at_start
            )

        if (
            time_at_apex is None
            or time_at_exit is None
        ):
            exit_time_change = None
        else:
            exit_time_change = (
                time_at_exit
                - time_at_apex
            )

        if (
            time_at_start is None
            or time_at_exit is None
        ):
            total_time_change = None
        else:
            total_time_change = (
                time_at_exit
                - time_at_start
            )

        return TrackCornerSegmentDelta(
            reference_corner_number=(
                reference.corner_number
            ),
            target_corner_number=(
                target.corner_number
            ),
            reference_braking_start_progress=(
                reference.start_progress
            ),
            target_braking_start_progress=(
                target.start_progress
            ),
            braking_start_progress_delta=(
                target.start_progress
                - reference.start_progress
            ),
            reference_turn_in_progress=(
                reference.turn_in_progress
            ),
            target_turn_in_progress=(
                target.turn_in_progress
            ),
            turn_in_progress_delta=(
                target.turn_in_progress
                - reference.turn_in_progress
            ),
            reference_apex_progress=(
                reference.apex_progress
            ),
            target_apex_progress=(
                target.apex_progress
            ),
            apex_progress_delta=(
                target.apex_progress
                - reference.apex_progress
            ),
            reference_throttle_application_progress=(
                reference
                .throttle_application_progress
            ),
            target_throttle_application_progress=(
                target
                .throttle_application_progress
            ),
            throttle_application_progress_delta=(
                target
                .throttle_application_progress
                - reference
                .throttle_application_progress
            ),
            reference_exit_progress=(
                reference.exit_progress
            ),
            target_exit_progress=(
                target.exit_progress
            ),
            exit_progress_delta=(
                target.exit_progress
                - reference.exit_progress
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
            reference_apex_speed_kmh=(
                reference.apex_speed_kmh
            ),
            target_apex_speed_kmh=(
                target.apex_speed_kmh
            ),
            apex_speed_delta_kmh=(
                target.apex_speed_kmh
                - reference.apex_speed_kmh
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
            reference_total_duration_seconds=(
                reference.total_duration_seconds
            ),
            target_total_duration_seconds=(
                target.total_duration_seconds
            ),
            total_duration_delta_seconds=(
                target.total_duration_seconds
                - reference.total_duration_seconds
            ),
            time_delta_at_start_seconds=(
                time_at_start
            ),
            time_delta_at_apex_seconds=(
                time_at_apex
            ),
            time_delta_at_exit_seconds=(
                time_at_exit
            ),
            time_delta_to_apex_change_seconds=(
                time_to_apex_change
            ),
            time_delta_exit_change_seconds=(
                exit_time_change
            ),
            time_delta_total_change_seconds=(
                total_time_change
            ),
        )

    def compare(
        self,
        *,
        reference_corners: tuple[
            TrackCornerSegment,
            ...,
        ],
        target_corners: tuple[
            TrackCornerSegment,
            ...,
        ],
        trace_comparison: LapTraceComparison,
    ) -> TrackSegmentationComparisonResult:
        matches = self._match_corners(
            reference_corners=(
                reference_corners
            ),
            target_corners=(
                target_corners
            ),
        )

        reference_numbers = {
            reference.corner_number
            for reference, _
            in matches
        }

        target_numbers = {
            target.corner_number
            for _, target
            in matches
        }

        deltas = tuple(
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
            corner.corner_number
            for corner in reference_corners
            if (
                corner.corner_number
                not in reference_numbers
            )
        )

        unmatched_target = tuple(
            corner.corner_number
            for corner in target_corners
            if (
                corner.corner_number
                not in target_numbers
            )
        )

        return TrackSegmentationComparisonResult(
            reference_lap_number=(
                trace_comparison
                .reference_lap_number
            ),
            target_lap_number=(
                trace_comparison
                .target_lap_number
            ),
            corners=deltas,
            unmatched_reference_corners=(
                unmatched_reference
            ),
            unmatched_target_corners=(
                unmatched_target
            ),
        )