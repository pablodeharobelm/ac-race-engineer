from bisect import bisect_left
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class DrivingTraceSample:
    """
    One telemetry sample located by normalized lap progress.

    progress:
        0.0 = start/finish
        1.0 = end of lap
    """

    progress: float
    elapsed_seconds: float

    speed_kmh: float

    throttle: float
    brake: float

    steering_angle_deg: float


@dataclass(frozen=True)
class AlignedTracePoint:
    progress: float

    reference_elapsed_seconds: float
    target_elapsed_seconds: float
    time_delta_seconds: float

    reference_speed_kmh: float
    target_speed_kmh: float
    speed_delta_kmh: float

    reference_throttle: float
    target_throttle: float
    throttle_delta: float

    reference_brake: float
    target_brake: float
    brake_delta: float

    reference_steering_angle_deg: float
    target_steering_angle_deg: float
    steering_delta_deg: float


@dataclass(frozen=True)
class LapTraceComparison:
    reference_lap_number: int
    target_lap_number: int

    start_progress: float
    end_progress: float

    points: tuple[
        AlignedTracePoint,
        ...,
    ]

    final_time_delta_seconds: float

    average_speed_delta_kmh: float

    largest_speed_loss_progress: float | None
    largest_speed_gain_progress: float | None


class AssettoCorsaTraceComparisonService:
    """
    Align two laps by normalized track position.

    All deltas use:

        target - reference

    Therefore:

        speed_delta < 0
            target is slower

        time_delta > 0
            target has lost time

        brake_delta > 0
            target uses more brake

        throttle_delta < 0
            target uses less throttle
    """

    @staticmethod
    def _validate_sample(
        sample: DrivingTraceSample,
    ) -> None:
        if not 0.0 <= sample.progress <= 1.0:
            raise ValueError(
                "Trace progress must be between 0 and 1"
            )

        if sample.elapsed_seconds < 0.0:
            raise ValueError(
                "Elapsed seconds cannot be negative"
            )

        if not 0.0 <= sample.throttle <= 1.0:
            raise ValueError(
                "Throttle must be between 0 and 1"
            )

        if not 0.0 <= sample.brake <= 1.0:
            raise ValueError(
                "Brake must be between 0 and 1"
            )

    def _prepare_trace(
        self,
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
    ) -> tuple[
        DrivingTraceSample,
        ...,
    ]:
        if len(samples) < 2:
            raise ValueError(
                "A trace requires at least two samples"
            )

        by_progress: dict[
            float,
            DrivingTraceSample,
        ] = {}

        for sample in samples:
            self._validate_sample(
                sample
            )

            by_progress[
                sample.progress
            ] = sample

        prepared = tuple(
            sorted(
                by_progress.values(),
                key=lambda sample: (
                    sample.progress
                ),
            )
        )

        if len(prepared) < 2:
            raise ValueError(
                "A trace requires at least two "
                "different progress positions"
            )

        previous_elapsed = (
            prepared[0].elapsed_seconds
        )

        for sample in prepared[1:]:
            if (
                sample.elapsed_seconds
                < previous_elapsed
            ):
                raise ValueError(
                    "Trace elapsed time must be "
                    "monotonically increasing"
                )

            previous_elapsed = (
                sample.elapsed_seconds
            )

        return prepared

    @staticmethod
    def _lerp(
        start: float,
        end: float,
        ratio: float,
    ) -> float:
        return (
            start
            + (
                end - start
            )
            * ratio
        )

    def _interpolate(
        self,
        *,
        samples: tuple[
            DrivingTraceSample,
            ...,
        ],
        positions: tuple[
            float,
            ...,
        ],
        progress: float,
    ) -> DrivingTraceSample:
        index = bisect_left(
            positions,
            progress,
        )

        if index <= 0:
            return samples[0]

        if index >= len(
            samples
        ):
            return samples[-1]

        right = samples[
            index
        ]

        left = samples[
            index - 1
        ]

        distance = (
            right.progress
            - left.progress
        )

        if distance <= 0.0:
            return right

        ratio = (
            progress
            - left.progress
        ) / distance

        return DrivingTraceSample(
            progress=progress,
            elapsed_seconds=self._lerp(
                left.elapsed_seconds,
                right.elapsed_seconds,
                ratio,
            ),
            speed_kmh=self._lerp(
                left.speed_kmh,
                right.speed_kmh,
                ratio,
            ),
            throttle=self._lerp(
                left.throttle,
                right.throttle,
                ratio,
            ),
            brake=self._lerp(
                left.brake,
                right.brake,
                ratio,
            ),
            steering_angle_deg=self._lerp(
                left.steering_angle_deg,
                right.steering_angle_deg,
                ratio,
            ),
        )

    def compare(
        self,
        *,
        reference_lap_number: int,
        target_lap_number: int,
        reference_trace: tuple[
            DrivingTraceSample,
            ...,
        ],
        target_trace: tuple[
            DrivingTraceSample,
            ...,
        ],
        grid_points: int = 201,
    ) -> LapTraceComparison:
        if (
            reference_lap_number
            == target_lap_number
        ):
            raise ValueError(
                "Reference and target laps "
                "must be different"
            )

        if grid_points < 2:
            raise ValueError(
                "grid_points must be at least 2"
            )

        reference = self._prepare_trace(
            reference_trace
        )

        target = self._prepare_trace(
            target_trace
        )

        start_progress = max(
            reference[0].progress,
            target[0].progress,
        )

        end_progress = min(
            reference[-1].progress,
            target[-1].progress,
        )

        if (
            end_progress
            <= start_progress
        ):
            raise ValueError(
                "Reference and target traces "
                "do not overlap"
            )

        reference_positions = tuple(
            sample.progress
            for sample in reference
        )

        target_positions = tuple(
            sample.progress
            for sample in target
        )

        progress_step = (
            end_progress
            - start_progress
        ) / (
            grid_points - 1
        )

        points: list[
            AlignedTracePoint
        ] = []

        for index in range(
            grid_points
        ):
            progress = (
                start_progress
                + progress_step
                * index
            )

            reference_sample = (
                self._interpolate(
                    samples=reference,
                    positions=(
                        reference_positions
                    ),
                    progress=progress,
                )
            )

            target_sample = (
                self._interpolate(
                    samples=target,
                    positions=(
                        target_positions
                    ),
                    progress=progress,
                )
            )

            points.append(
                AlignedTracePoint(
                    progress=progress,
                    reference_elapsed_seconds=(
                        reference_sample.elapsed_seconds
                    ),
                    target_elapsed_seconds=(
                        target_sample.elapsed_seconds
                    ),
                    time_delta_seconds=(
                        target_sample.elapsed_seconds
                        - reference_sample.elapsed_seconds
                    ),
                    reference_speed_kmh=(
                        reference_sample.speed_kmh
                    ),
                    target_speed_kmh=(
                        target_sample.speed_kmh
                    ),
                    speed_delta_kmh=(
                        target_sample.speed_kmh
                        - reference_sample.speed_kmh
                    ),
                    reference_throttle=(
                        reference_sample.throttle
                    ),
                    target_throttle=(
                        target_sample.throttle
                    ),
                    throttle_delta=(
                        target_sample.throttle
                        - reference_sample.throttle
                    ),
                    reference_brake=(
                        reference_sample.brake
                    ),
                    target_brake=(
                        target_sample.brake
                    ),
                    brake_delta=(
                        target_sample.brake
                        - reference_sample.brake
                    ),
                    reference_steering_angle_deg=(
                        reference_sample.steering_angle_deg
                    ),
                    target_steering_angle_deg=(
                        target_sample.steering_angle_deg
                    ),
                    steering_delta_deg=(
                        target_sample.steering_angle_deg
                        - reference_sample.steering_angle_deg
                    ),
                )
            )

        speed_loss_points = [
            point
            for point in points
            if point.speed_delta_kmh < 0.0
        ]

        speed_gain_points = [
            point
            for point in points
            if point.speed_delta_kmh > 0.0
        ]

        largest_speed_loss_progress = None

        if speed_loss_points:
            largest_speed_loss_progress = min(
                speed_loss_points,
                key=lambda point: (
                    point.speed_delta_kmh
                ),
            ).progress

        largest_speed_gain_progress = None

        if speed_gain_points:
            largest_speed_gain_progress = max(
                speed_gain_points,
                key=lambda point: (
                    point.speed_delta_kmh
                ),
            ).progress

        return LapTraceComparison(
            reference_lap_number=(
                reference_lap_number
            ),
            target_lap_number=(
                target_lap_number
            ),
            start_progress=(
                start_progress
            ),
            end_progress=(
                end_progress
            ),
            points=tuple(
                points
            ),
            final_time_delta_seconds=(
                points[
                    -1
                ].time_delta_seconds
            ),
            average_speed_delta_kmh=fmean(
                point.speed_delta_kmh
                for point in points
            ),
            largest_speed_loss_progress=(
                largest_speed_loss_progress
            ),
            largest_speed_gain_progress=(
                largest_speed_gain_progress
            ),
        )
    