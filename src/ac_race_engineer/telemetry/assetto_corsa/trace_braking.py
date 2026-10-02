from dataclasses import dataclass
from statistics import fmean

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)


@dataclass(frozen=True)
class BrakingZone:
    zone_number: int

    start_progress: float
    end_progress: float

    start_elapsed_seconds: float
    end_elapsed_seconds: float
    duration_seconds: float

    entry_speed_kmh: float
    minimum_speed_kmh: float
    exit_speed_kmh: float

    peak_brake: float
    average_brake: float

    sample_count: int

    @property
    def center_progress(
        self,
    ) -> float:
        return (
            self.start_progress
            + self.end_progress
        ) / 2.0

    @property
    def progress_span(
        self,
    ) -> float:
        return (
            self.end_progress
            - self.start_progress
        )


class AssettoCorsaBrakingZoneService:
    """
    Detect braking zones inside a driving trace.

    A braking zone is a contiguous group of samples
    whose brake input is greater than or equal to the
    configured threshold.

    This service describes measured telemetry only.
    It does not infer driving mistakes or recommend
    braking changes.
    """

    def __init__(
        self,
        *,
        brake_threshold: float = 0.10,
        minimum_samples: int = 2,
    ) -> None:
        if not (
            0.0
            < brake_threshold
            <= 1.0
        ):
            raise ValueError(
                "brake_threshold must be "
                "greater than 0 and at most 1"
            )

        if minimum_samples <= 0:
            raise ValueError(
                "minimum_samples must be "
                "greater than 0"
            )

        self.brake_threshold = (
            brake_threshold
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
        previous_progress: (
            float | None
        ) = None

        previous_elapsed: (
            float | None
        ) = None

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

    def _build_zone(
        self,
        *,
        zone_number: int,
        samples: list[
            DrivingTraceSample
        ],
    ) -> BrakingZone:
        first = samples[0]
        last = samples[-1]

        speeds = [
            sample.speed_kmh
            for sample in samples
        ]

        brake_values = [
            sample.brake
            for sample in samples
        ]

        return BrakingZone(
            zone_number=zone_number,
            start_progress=(
                first.progress
            ),
            end_progress=(
                last.progress
            ),
            start_elapsed_seconds=(
                first.elapsed_seconds
            ),
            end_elapsed_seconds=(
                last.elapsed_seconds
            ),
            duration_seconds=max(
                0.0,
                (
                    last.elapsed_seconds
                    - first.elapsed_seconds
                ),
            ),
            entry_speed_kmh=(
                first.speed_kmh
            ),
            minimum_speed_kmh=min(
                speeds
            ),
            exit_speed_kmh=(
                last.speed_kmh
            ),
            peak_brake=max(
                brake_values
            ),
            average_brake=fmean(
                brake_values
            ),
            sample_count=len(
                samples
            ),
        )

    def analyze(
        self,
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
    ) -> tuple[
        BrakingZone,
        ...,
    ]:
        if not samples:
            return ()

        self._validate_samples(
            samples
        )

        zones: list[
            BrakingZone
        ] = []

        current_samples: list[
            DrivingTraceSample
        ] = []

        def finish_current_zone() -> None:
            if (
                len(
                    current_samples
                )
                < self.minimum_samples
            ):
                current_samples.clear()
                return

            zone = self._build_zone(
                zone_number=(
                    len(zones) + 1
                ),
                samples=current_samples,
            )

            zones.append(
                zone
            )

            current_samples.clear()

        for sample in samples:
            is_braking = (
                sample.brake
                >= self.brake_threshold
            )

            if is_braking:
                current_samples.append(
                    sample
                )

                continue

            if current_samples:
                finish_current_zone()

        if current_samples:
            finish_current_zone()

        return tuple(
            zones
        )