from bisect import bisect_left
from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit import (
    CornerExit,
)


@dataclass(frozen=True)
class CornerExitDelta:
    reference_exit_number: int
    target_exit_number: int

    reference_apex_progress: float
    target_apex_progress: float

    reference_exit_progress: float
    target_exit_progress: float
    exit_progress_delta: float

    reference_throttle_application_progress: float
    target_throttle_application_progress: float
    throttle_application_progress_delta: float

    reference_duration_seconds: float
    target_duration_seconds: float
    duration_delta_seconds: float

    reference_time_to_throttle_seconds: float
    target_time_to_throttle_seconds: float
    time_to_throttle_delta_seconds: float

    reference_apex_speed_kmh: float
    target_apex_speed_kmh: float
    apex_speed_delta_kmh: float

    reference_exit_speed_kmh: float
    target_exit_speed_kmh: float
    exit_speed_delta_kmh: float

    reference_speed_gain_kmh: float
    target_speed_gain_kmh: float
    speed_gain_delta_kmh: float

    reference_throttle_at_exit: float
    target_throttle_at_exit: float
    throttle_at_exit_delta: float

    reference_abs_steering_at_exit_deg: float
    target_abs_steering_at_exit_deg: float
    abs_steering_at_exit_delta_deg: float

    reference_steering_unwind_deg: float
    target_steering_unwind_deg: float
    steering_unwind_delta_deg: float

    time_delta_at_apex_seconds: float | None
    time_delta_at_exit_seconds: float | None
    time_delta_change_seconds: float | None

    @property
    def target_applies_throttle_earlier(
        self,
    ) -> bool:
        return (
            self.throttle_application_progress_delta
            < 0.0
        )

    @property
    def target_applies_throttle_later(
        self,
    ) -> bool:
        return (
            self.throttle_application_progress_delta
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
class CornerExitComparisonResult:
    reference_lap_number: int
    target_lap_number: int

    exits: tuple[
        CornerExitDelta,
        ...,
    ]

    unmatched_reference_exits: tuple[
        int,
        ...,
    ]

    unmatched_target_exits: tuple[
        int,
        ...,
    ]

    @property
    def matched_exit_count(
        self,
    ) -> int:
        return len(
            self.exits
        )

    @property
    def total_time_lost_seconds(
        self,
    ) -> float:
        return sum(
            corner_exit.time_lost_seconds
            or 0.0
            for corner_exit in self.exits
        )

    @property
    def total_time_gained_seconds(
        self,
    ) -> float:
        return sum(
            corner_exit.time_gained_seconds
            or 0.0
            for corner_exit in self.exits
        )


class AssettoCorsaCornerExitComparisonService:
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
        reference: CornerExit,
        target: CornerExit,
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
        reference: CornerExit,
        target: CornerExit,
    ) -> float:
        return abs(
            target.apex_progress
            - reference.apex_progress
        )

    def _select_target(
        self,
        *,
        reference: CornerExit,
        candidates: list[
            CornerExit
        ],
    ) -> CornerExit:
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

    def _match_exits(
        self,
        reference_exits: tuple[
            CornerExit,
            ...,
        ],
        target_exits: tuple[
            CornerExit,
            ...,
        ],
    ) -> tuple[
        tuple[
            CornerExit,
            CornerExit,
        ],
        ...,
    ]:
        available_targets = list(
            target_exits
        )

        matches: list[
            tuple[
                CornerExit,
                CornerExit,
            ]
        ] = []

        ordered_reference = sorted(
            reference_exits,
            key=lambda item: (
                item.apex_progress
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
        reference: CornerExit,
        target: CornerExit,
        trace_comparison: LapTraceComparison,
    ) -> CornerExitDelta:
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
            time_at_apex is None
            or time_at_exit is None
        ):
            time_change = None

        else:
            time_change = (
                time_at_exit
                - time_at_apex
            )

        reference_exit_steering = abs(
            reference.steering_at_exit_deg
        )

        target_exit_steering = abs(
            target.steering_at_exit_deg
        )

        return CornerExitDelta(
            reference_exit_number=(
                reference.exit_number
            ),
            target_exit_number=(
                target.exit_number
            ),
            reference_apex_progress=(
                reference.apex_progress
            ),
            target_apex_progress=(
                target.apex_progress
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
            reference_time_to_throttle_seconds=(
                reference
                .time_to_throttle_seconds
            ),
            target_time_to_throttle_seconds=(
                target
                .time_to_throttle_seconds
            ),
            time_to_throttle_delta_seconds=(
                target.time_to_throttle_seconds
                - reference.time_to_throttle_seconds
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
            reference_speed_gain_kmh=(
                reference.speed_gain_kmh
            ),
            target_speed_gain_kmh=(
                target.speed_gain_kmh
            ),
            speed_gain_delta_kmh=(
                target.speed_gain_kmh
                - reference.speed_gain_kmh
            ),
            reference_throttle_at_exit=(
                reference.throttle_at_exit
            ),
            target_throttle_at_exit=(
                target.throttle_at_exit
            ),
            throttle_at_exit_delta=(
                target.throttle_at_exit
                - reference.throttle_at_exit
            ),
            reference_abs_steering_at_exit_deg=(
                reference_exit_steering
            ),
            target_abs_steering_at_exit_deg=(
                target_exit_steering
            ),
            abs_steering_at_exit_delta_deg=(
                target_exit_steering
                - reference_exit_steering
            ),
            reference_steering_unwind_deg=(
                reference.steering_unwind_deg
            ),
            target_steering_unwind_deg=(
                target.steering_unwind_deg
            ),
            steering_unwind_delta_deg=(
                target.steering_unwind_deg
                - reference.steering_unwind_deg
            ),
            time_delta_at_apex_seconds=(
                time_at_apex
            ),
            time_delta_at_exit_seconds=(
                time_at_exit
            ),
            time_delta_change_seconds=(
                time_change
            ),
        )

    def compare(
        self,
        *,
        reference_exits: tuple[
            CornerExit,
            ...,
        ],
        target_exits: tuple[
            CornerExit,
            ...,
        ],
        trace_comparison: LapTraceComparison,
    ) -> CornerExitComparisonResult:
        matches = self._match_exits(
            reference_exits,
            target_exits,
        )

        reference_numbers = {
            reference.exit_number
            for reference, _
            in matches
        }

        target_numbers = {
            target.exit_number
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

        return CornerExitComparisonResult(
            reference_lap_number=(
                trace_comparison
                .reference_lap_number
            ),
            target_lap_number=(
                trace_comparison
                .target_lap_number
            ),
            exits=deltas,
            unmatched_reference_exits=tuple(
                item.exit_number
                for item in reference_exits
                if (
                    item.exit_number
                    not in reference_numbers
                )
            ),
            unmatched_target_exits=tuple(
                item.exit_number
                for item in target_exits
                if (
                    item.exit_number
                    not in target_numbers
                )
            ),
        )