from bisect import bisect_left
from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AlignedTracePoint,
    LapTraceComparison,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    CornerEntry,
)


@dataclass(frozen=True)
class CornerEntryDelta:
    reference_entry_number: int
    target_entry_number: int

    reference_turn_in_progress: float
    target_turn_in_progress: float
    turn_in_progress_delta: float

    reference_apex_progress: float
    target_apex_progress: float
    apex_progress_delta: float

    reference_entry_duration_seconds: float
    target_entry_duration_seconds: float
    entry_duration_delta_seconds: float

    reference_brake_overlap_seconds: float
    target_brake_overlap_seconds: float
    brake_overlap_delta_seconds: float

    reference_entry_speed_kmh: float
    target_entry_speed_kmh: float
    entry_speed_delta_kmh: float

    reference_apex_speed_kmh: float
    target_apex_speed_kmh: float
    apex_speed_delta_kmh: float

    reference_speed_loss_kmh: float
    target_speed_loss_kmh: float
    speed_loss_delta_kmh: float

    reference_brake_at_turn_in: float
    target_brake_at_turn_in: float
    brake_at_turn_in_delta: float

    reference_throttle_at_turn_in: float
    target_throttle_at_turn_in: float
    throttle_at_turn_in_delta: float

    reference_throttle_at_apex: float
    target_throttle_at_apex: float
    throttle_at_apex_delta: float

    reference_maximum_abs_steering_deg: float
    target_maximum_abs_steering_deg: float
    maximum_abs_steering_delta_deg: float

    reference_average_abs_steering_deg: float
    target_average_abs_steering_deg: float
    average_abs_steering_delta_deg: float

    time_delta_at_turn_in_seconds: float | None
    time_delta_at_apex_seconds: float | None
    time_delta_change_seconds: float | None

    overlap_progress: float
    overlap_ratio: float

    @property
    def target_turns_in_earlier(
        self,
    ) -> bool:
        return (
            self.turn_in_progress_delta
            < 0.0
        )

    @property
    def target_turns_in_later(
        self,
    ) -> bool:
        return (
            self.turn_in_progress_delta
            > 0.0
        )

    @property
    def target_reaches_apex_earlier(
        self,
    ) -> bool:
        return (
            self.apex_progress_delta
            < 0.0
        )

    @property
    def target_reaches_apex_later(
        self,
    ) -> bool:
        return (
            self.apex_progress_delta
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
class CornerEntryComparisonResult:
    reference_lap_number: int
    target_lap_number: int

    entries: tuple[
        CornerEntryDelta,
        ...,
    ]

    unmatched_reference_entries: tuple[
        int,
        ...,
    ]

    unmatched_target_entries: tuple[
        int,
        ...,
    ]

    @property
    def matched_entry_count(
        self,
    ) -> int:
        return len(
            self.entries
        )

    @property
    def total_time_lost_seconds(
        self,
    ) -> float:
        return sum(
            entry.time_lost_seconds
            or 0.0
            for entry in self.entries
        )

    @property
    def total_time_gained_seconds(
        self,
    ) -> float:
        return sum(
            entry.time_gained_seconds
            or 0.0
            for entry in self.entries
        )


class AssettoCorsaCornerEntryComparisonService:
    """
    Compare corner entries between two aligned laps.

    Entry matching is based on track position,
    not entry number.

    Delta convention:

        target - reference

    Therefore:

        turn_in_progress_delta < 0
            target turns in earlier

        turn_in_progress_delta > 0
            target turns in later

        apex_speed_delta_kmh < 0
            target reaches a lower apex speed

        brake_overlap_delta_seconds > 0
            target carries the brake for longer
            after turn-in

        time_delta_change_seconds > 0
            target loses time from turn-in to apex

        time_delta_change_seconds < 0
            target gains time from turn-in to apex
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
    def _entry_center(
        entry: CornerEntry,
    ) -> float:
        return (
            entry.turn_in_progress
            + entry.apex_progress
        ) / 2.0

    @staticmethod
    def _entry_span(
        entry: CornerEntry,
    ) -> float:
        return max(
            0.0,
            (
                entry.apex_progress
                - entry.turn_in_progress
            ),
        )

    @staticmethod
    def _overlap(
        reference: CornerEntry,
        target: CornerEntry,
    ) -> float:
        start = max(
            reference.turn_in_progress,
            target.turn_in_progress,
        )

        end = min(
            reference.apex_progress,
            target.apex_progress,
        )

        return max(
            0.0,
            end - start,
        )

    @classmethod
    def _overlap_ratio(
        cls,
        reference: CornerEntry,
        target: CornerEntry,
    ) -> float:
        overlap = cls._overlap(
            reference,
            target,
        )

        if overlap <= 0.0:
            return 0.0

        reference_span = (
            cls._entry_span(
                reference
            )
        )

        target_span = (
            cls._entry_span(
                target
            )
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

    def _entries_can_match(
        self,
        reference: CornerEntry,
        target: CornerEntry,
    ) -> bool:
        overlap_ratio = (
            self._overlap_ratio(
                reference,
                target,
            )
        )

        center_distance = abs(
            self._entry_center(
                target
            )
            - self._entry_center(
                reference
            )
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
        reference: CornerEntry,
        target: CornerEntry,
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
            self._entry_center(
                target
            )
            - self._entry_center(
                reference
            )
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
        reference: CornerEntry,
        candidates: list[
            CornerEntry
        ],
    ) -> CornerEntry:
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

    def _match_entries(
        self,
        reference_entries: tuple[
            CornerEntry,
            ...,
        ],
        target_entries: tuple[
            CornerEntry,
            ...,
        ],
    ) -> tuple[
        tuple[
            CornerEntry,
            CornerEntry,
        ],
        ...,
    ]:
        available_targets = list(
            target_entries
        )

        matches: list[
            tuple[
                CornerEntry,
                CornerEntry,
            ]
        ] = []

        ordered_reference = sorted(
            reference_entries,
            key=self._entry_center,
        )

        for reference in ordered_reference:
            candidates = [
                target
                for target
                in available_targets
                if self._entries_can_match(
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
        reference: CornerEntry,
        target: CornerEntry,
        trace_comparison: LapTraceComparison,
    ) -> CornerEntryDelta:
        turn_in_time_delta = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.turn_in_progress,
            )
        )

        apex_time_delta = (
            self._interpolate_time_delta(
                trace_comparison.points,
                reference.apex_progress,
            )
        )

        time_delta_change: (
            float | None
        )

        if (
            turn_in_time_delta is None
            or apex_time_delta is None
        ):
            time_delta_change = None

        else:
            time_delta_change = (
                apex_time_delta
                - turn_in_time_delta
            )

        return CornerEntryDelta(
            reference_entry_number=(
                reference.entry_number
            ),
            target_entry_number=(
                target.entry_number
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
            reference_entry_duration_seconds=(
                reference.entry_duration_seconds
            ),
            target_entry_duration_seconds=(
                target.entry_duration_seconds
            ),
            entry_duration_delta_seconds=(
                target.entry_duration_seconds
                - reference.entry_duration_seconds
            ),
            reference_brake_overlap_seconds=(
                reference.brake_overlap_seconds
            ),
            target_brake_overlap_seconds=(
                target.brake_overlap_seconds
            ),
            brake_overlap_delta_seconds=(
                target.brake_overlap_seconds
                - reference.brake_overlap_seconds
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
            reference_speed_loss_kmh=(
                reference.speed_loss_kmh
            ),
            target_speed_loss_kmh=(
                target.speed_loss_kmh
            ),
            speed_loss_delta_kmh=(
                target.speed_loss_kmh
                - reference.speed_loss_kmh
            ),
            reference_brake_at_turn_in=(
                reference.brake_at_turn_in
            ),
            target_brake_at_turn_in=(
                target.brake_at_turn_in
            ),
            brake_at_turn_in_delta=(
                target.brake_at_turn_in
                - reference.brake_at_turn_in
            ),
            reference_throttle_at_turn_in=(
                reference.throttle_at_turn_in
            ),
            target_throttle_at_turn_in=(
                target.throttle_at_turn_in
            ),
            throttle_at_turn_in_delta=(
                target.throttle_at_turn_in
                - reference.throttle_at_turn_in
            ),
            reference_throttle_at_apex=(
                reference.throttle_at_apex
            ),
            target_throttle_at_apex=(
                target.throttle_at_apex
            ),
            throttle_at_apex_delta=(
                target.throttle_at_apex
                - reference.throttle_at_apex
            ),
            reference_maximum_abs_steering_deg=(
                reference.maximum_abs_steering_deg
            ),
            target_maximum_abs_steering_deg=(
                target.maximum_abs_steering_deg
            ),
            maximum_abs_steering_delta_deg=(
                target.maximum_abs_steering_deg
                - reference.maximum_abs_steering_deg
            ),
            reference_average_abs_steering_deg=(
                reference.average_abs_steering_deg
            ),
            target_average_abs_steering_deg=(
                target.average_abs_steering_deg
            ),
            average_abs_steering_delta_deg=(
                target.average_abs_steering_deg
                - reference.average_abs_steering_deg
            ),
            time_delta_at_turn_in_seconds=(
                turn_in_time_delta
            ),
            time_delta_at_apex_seconds=(
                apex_time_delta
            ),
            time_delta_change_seconds=(
                time_delta_change
            ),
            overlap_progress=(
                self._overlap(
                    reference,
                    target,
                )
            ),
            overlap_ratio=(
                self._overlap_ratio(
                    reference,
                    target,
                )
            ),
        )

    def compare(
        self,
        *,
        reference_entries: tuple[
            CornerEntry,
            ...,
        ],
        target_entries: tuple[
            CornerEntry,
            ...,
        ],
        trace_comparison: LapTraceComparison,
    ) -> CornerEntryComparisonResult:
        matches = self._match_entries(
            reference_entries,
            target_entries,
        )

        matched_reference_numbers = {
            reference.entry_number
            for reference, _
            in matches
        }

        matched_target_numbers = {
            target.entry_number
            for _, target
            in matches
        }

        entries = tuple(
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
            entry.entry_number
            for entry in reference_entries
            if (
                entry.entry_number
                not in matched_reference_numbers
            )
        )

        unmatched_target = tuple(
            entry.entry_number
            for entry in target_entries
            if (
                entry.entry_number
                not in matched_target_numbers
            )
        )

        return CornerEntryComparisonResult(
            reference_lap_number=(
                trace_comparison
                .reference_lap_number
            ),
            target_lap_number=(
                trace_comparison
                .target_lap_number
            ),
            entries=entries,
            unmatched_reference_entries=(
                unmatched_reference
            ),
            unmatched_target_entries=(
                unmatched_target
            ),
        )