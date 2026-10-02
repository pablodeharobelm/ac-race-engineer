from dataclasses import dataclass
from statistics import fmean

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    BrakingZone,
)


@dataclass(frozen=True)
class CornerEntry:
    entry_number: int
    source_braking_zone_number: int

    braking_start_progress: float
    brake_release_progress: float

    turn_in_progress: float
    apex_progress: float

    turn_in_elapsed_seconds: float
    brake_release_elapsed_seconds: float
    apex_elapsed_seconds: float

    entry_duration_seconds: float
    brake_overlap_seconds: float

    entry_speed_kmh: float
    apex_speed_kmh: float
    speed_loss_kmh: float

    brake_at_turn_in: float

    throttle_at_turn_in: float
    throttle_at_apex: float

    steering_at_turn_in_deg: float
    maximum_abs_steering_deg: float
    average_abs_steering_deg: float

    sample_count: int

    @property
    def turn_in_before_brake_release(
        self,
    ) -> bool:
        return (
            self.turn_in_elapsed_seconds
            < self.brake_release_elapsed_seconds
        )

    @property
    def progress_to_apex(
        self,
    ) -> float:
        return (
            self.apex_progress
            - self.turn_in_progress
        )


class AssettoCorsaCornerEntryService:
    """
    Detect corner-entry phases associated with braking zones.

    For each braking zone:

    1. Search for steering input around the braking phase.
    2. Detect the first meaningful steering sample as turn-in.
    3. Search forward for the minimum speed.
    4. Treat that minimum-speed point as an apex proxy.
    5. Measure the brake-to-steering transition.

    This service only describes telemetry.

    It does not diagnose whether the driver entered the
    corner correctly.
    """

    def __init__(
        self,
        *,
        steering_threshold_deg: float = 5.0,
        lookahead_progress: float = 0.08,
        minimum_samples: int = 2,
    ) -> None:
        if steering_threshold_deg <= 0.0:
            raise ValueError(
                "steering_threshold_deg must be "
                "greater than 0"
            )

        if not (
            0.0
            < lookahead_progress
            <= 1.0
        ):
            raise ValueError(
                "lookahead_progress must be "
                "greater than 0 and at most 1"
            )

        if minimum_samples < 2:
            raise ValueError(
                "minimum_samples must be at least 2"
            )

        self.steering_threshold_deg = (
            steering_threshold_deg
        )

        self.lookahead_progress = (
            lookahead_progress
        )

        self.minimum_samples = (
            minimum_samples
        )

    @staticmethod
    def _validate_samples(
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
    ) -> None:
        previous_progress: float | None = None
        previous_elapsed: float | None = None

        for sample in samples:
            if not (
                0.0
                <= sample.progress
                <= 1.0
            ):
                raise ValueError(
                    "Trace progress must be "
                    "between 0 and 1"
                )

            if sample.elapsed_seconds < 0.0:
                raise ValueError(
                    "Elapsed seconds cannot "
                    "be negative"
                )

            if not (
                0.0
                <= sample.brake
                <= 1.0
            ):
                raise ValueError(
                    "Brake input must be "
                    "between 0 and 1"
                )

            if not (
                0.0
                <= sample.throttle
                <= 1.0
            ):
                raise ValueError(
                    "Throttle input must be "
                    "between 0 and 1"
                )

            if (
                previous_progress is not None
                and sample.progress
                < previous_progress
            ):
                raise ValueError(
                    "Trace progress must be "
                    "monotonically increasing"
                )

            if (
                previous_elapsed is not None
                and sample.elapsed_seconds
                < previous_elapsed
            ):
                raise ValueError(
                    "Trace elapsed time must be "
                    "monotonically increasing"
                )

            previous_progress = (
                sample.progress
            )

            previous_elapsed = (
                sample.elapsed_seconds
            )

    def _samples_for_zone(
        self,
        *,
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
        zone: BrakingZone,
    ) -> tuple[
        DrivingTraceSample,
        ...,
    ]:
        end_progress = min(
            1.0,
            (
                zone.end_progress
                + self.lookahead_progress
            ),
        )

        return tuple(
            sample
            for sample in samples
            if (
                zone.start_progress
                <= sample.progress
                <= end_progress
            )
        )

    def _find_turn_in_index(
        self,
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
    ) -> int | None:
        for index, sample in enumerate(
            samples
        ):
            if (
                abs(
                    sample.steering_angle_deg
                )
                >= self.steering_threshold_deg
            ):
                return index

        return None

    @staticmethod
    def _find_apex_index(
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
    ) -> int:
        return min(
            range(
                len(samples)
            ),
            key=lambda index: (
                samples[index].speed_kmh,
                samples[index].progress,
            ),
        )

    def _build_entry(
        self,
        *,
        entry_number: int,
        zone: BrakingZone,
        zone_samples: tuple[
            DrivingTraceSample,
            ...,
        ],
    ) -> CornerEntry | None:
        turn_in_index = (
            self._find_turn_in_index(
                zone_samples
            )
        )

        if turn_in_index is None:
            return None

        entry_samples = (
            zone_samples[
                turn_in_index:
            ]
        )

        if (
            len(entry_samples)
            < self.minimum_samples
        ):
            return None

        apex_index = (
            self._find_apex_index(
                entry_samples
            )
        )

        analysis_samples = (
            entry_samples[
                : apex_index + 1
            ]
        )

        if (
            len(analysis_samples)
            < self.minimum_samples
        ):
            return None

        turn_in = (
            analysis_samples[0]
        )

        apex = (
            analysis_samples[-1]
        )

        steering_values = [
            abs(
                sample.steering_angle_deg
            )
            for sample in analysis_samples
        ]

        entry_duration = max(
            0.0,
            (
                apex.elapsed_seconds
                - turn_in.elapsed_seconds
            ),
        )

        brake_overlap = max(
            0.0,
            (
                zone.end_elapsed_seconds
                - turn_in.elapsed_seconds
            ),
        )

        speed_loss = max(
            0.0,
            (
                turn_in.speed_kmh
                - apex.speed_kmh
            ),
        )

        return CornerEntry(
            entry_number=entry_number,
            source_braking_zone_number=(
                zone.zone_number
            ),
            braking_start_progress=(
                zone.start_progress
            ),
            brake_release_progress=(
                zone.end_progress
            ),
            turn_in_progress=(
                turn_in.progress
            ),
            apex_progress=(
                apex.progress
            ),
            turn_in_elapsed_seconds=(
                turn_in.elapsed_seconds
            ),
            brake_release_elapsed_seconds=(
                zone.end_elapsed_seconds
            ),
            apex_elapsed_seconds=(
                apex.elapsed_seconds
            ),
            entry_duration_seconds=(
                entry_duration
            ),
            brake_overlap_seconds=(
                brake_overlap
            ),
            entry_speed_kmh=(
                turn_in.speed_kmh
            ),
            apex_speed_kmh=(
                apex.speed_kmh
            ),
            speed_loss_kmh=(
                speed_loss
            ),
            brake_at_turn_in=(
                turn_in.brake
            ),
            throttle_at_turn_in=(
                turn_in.throttle
            ),
            throttle_at_apex=(
                apex.throttle
            ),
            steering_at_turn_in_deg=(
                turn_in.steering_angle_deg
            ),
            maximum_abs_steering_deg=max(
                steering_values
            ),
            average_abs_steering_deg=fmean(
                steering_values
            ),
            sample_count=len(
                analysis_samples
            ),
        )

    def analyze(
        self,
        *,
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
        braking_zones: tuple[
            BrakingZone,
            ...,
        ],
    ) -> tuple[
        CornerEntry,
        ...,
    ]:
        if not samples:
            return ()

        if not braking_zones:
            return ()

        self._validate_samples(
            samples
        )

        entries: list[
            CornerEntry
        ] = []

        for zone in braking_zones:
            zone_samples = (
                self._samples_for_zone(
                    samples=samples,
                    zone=zone,
                )
            )

            if (
                len(zone_samples)
                < self.minimum_samples
            ):
                continue

            entry = (
                self._build_entry(
                    entry_number=(
                        len(entries) + 1
                    ),
                    zone=zone,
                    zone_samples=zone_samples,
                )
            )

            if entry is None:
                continue

            entries.append(
                entry
            )

        return tuple(
            entries
        )