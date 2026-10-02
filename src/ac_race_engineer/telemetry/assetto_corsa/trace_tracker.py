from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
)
from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)


@dataclass(frozen=True)
class LapTrace:
    session_id: str
    lap_number: int

    car_id: str
    track_id: str

    lap_time_ms: int

    samples: tuple[
        DrivingTraceSample,
        ...,
    ]

    @property
    def sample_count(
        self,
    ) -> int:
        return len(
            self.samples
        )


class AssettoCorsaLapTraceTracker:
    """
    Build complete lap traces from Assetto Corsa telemetry.

    The tracker intentionally discards the first observed lap
    when capture starts in the middle of a lap.

    Recording starts immediately only when capture begins
    sufficiently close to start/finish and the current lap
    time is also close to zero.
    """

    def __init__(
        self,
        *,
        start_progress_threshold: float = 0.05,
        end_progress_threshold: float = 0.90,
        start_time_threshold_seconds: float = 5.0,
        minimum_samples: int = 3,
    ) -> None:
        if not (
            0.0
            <= start_progress_threshold
            < 1.0
        ):
            raise ValueError(
                "start_progress_threshold must "
                "be between 0 and 1"
            )

        if not (
            0.0
            < end_progress_threshold
            <= 1.0
        ):
            raise ValueError(
                "end_progress_threshold must "
                "be between 0 and 1"
            )

        if (
            end_progress_threshold
            <= start_progress_threshold
        ):
            raise ValueError(
                "end_progress_threshold must be "
                "greater than start_progress_threshold"
            )

        if (
            start_time_threshold_seconds
            < 0.0
        ):
            raise ValueError(
                "start_time_threshold_seconds "
                "cannot be negative"
            )

        if minimum_samples < 2:
            raise ValueError(
                "minimum_samples must be at least 2"
            )

        self.start_progress_threshold = (
            start_progress_threshold
        )

        self.end_progress_threshold = (
            end_progress_threshold
        )

        self.start_time_threshold_seconds = (
            start_time_threshold_seconds
        )

        self.minimum_samples = (
            minimum_samples
        )

        self._previous_completed_laps: (
            int | None
        ) = None

        self._recording = False

        self._current_lap_number: (
            int | None
        ) = None

        self._current_session_id: (
            str | None
        ) = None

        self._current_car_id: (
            str | None
        ) = None

        self._current_track_id: (
            str | None
        ) = None

        self._samples: list[
            DrivingTraceSample
        ] = []

    def reset(
        self,
    ) -> None:
        self._previous_completed_laps = None
        self._discard_current_trace()

    def _discard_current_trace(
        self,
    ) -> None:
        self._recording = False

        self._current_lap_number = None
        self._current_session_id = None
        self._current_car_id = None
        self._current_track_id = None

        self._samples = []

    @staticmethod
    def _progress(
        graphics: ACGraphicsSnapshot,
    ) -> float:
        return min(
            1.0,
            max(
                0.0,
                graphics.normalized_car_position,
            ),
        )

    @staticmethod
    def _lap_elapsed_seconds(
        graphics: ACGraphicsSnapshot,
    ) -> float:
        return max(
            0.0,
            graphics.current_time_ms
            / 1000.0,
        )

    def _can_start_immediately(
        self,
        *,
        progress: float,
        lap_elapsed_seconds: float,
    ) -> bool:
        return (
            progress
            <= self.start_progress_threshold
            and lap_elapsed_seconds
            <= self.start_time_threshold_seconds
        )

    def _start_trace(
        self,
        *,
        frame: TelemetryFrame,
        lap_number: int,
    ) -> None:
        self._recording = True

        self._current_lap_number = (
            lap_number
        )

        self._current_session_id = (
            frame.session_id
        )

        self._current_car_id = (
            frame.car_id
        )

        self._current_track_id = (
            frame.track_id
        )

        self._samples = []

    def _append_sample(
        self,
        *,
        frame: TelemetryFrame,
        graphics: ACGraphicsSnapshot,
    ) -> None:
        if not self._recording:
            return

        sample = DrivingTraceSample(
            progress=self._progress(
                graphics
            ),
            elapsed_seconds=(
                self._lap_elapsed_seconds(
                    graphics
                )
            ),
            speed_kmh=(
                frame.vehicle.speed_kmh
            ),
            throttle=(
                frame.vehicle.throttle
            ),
            brake=(
                frame.vehicle.brake
            ),
            steering_angle_deg=(
                frame.vehicle.steering_angle_deg
            ),
        )

        if self._samples:
            previous = (
                self._samples[-1]
            )

            if (
                sample.elapsed_seconds
                < previous.elapsed_seconds
            ):
                return

            if (
                sample.progress
                < previous.progress
            ):
                return

            if (
                sample.progress
                == previous.progress
            ):
                self._samples[-1] = sample
                return

        self._samples.append(
            sample
        )

    def _finish_trace(
        self,
        *,
        lap_time_ms: int,
    ) -> LapTrace | None:
        if not self._recording:
            return None

        samples = tuple(
            self._samples
        )

        lap_number = (
            self._current_lap_number
        )

        session_id = (
            self._current_session_id
        )

        car_id = (
            self._current_car_id
        )

        track_id = (
            self._current_track_id
        )

        self._discard_current_trace()

        if (
            lap_number is None
            or session_id is None
            or car_id is None
            or track_id is None
        ):
            return None

        if (
            len(samples)
            < self.minimum_samples
        ):
            return None

        if (
            samples[0].progress
            > self.start_progress_threshold
        ):
            return None

        if (
            samples[-1].progress
            < self.end_progress_threshold
        ):
            return None

        if lap_time_ms <= 0:
            return None

        return LapTrace(
            session_id=session_id,
            lap_number=lap_number,
            car_id=car_id,
            track_id=track_id,
            lap_time_ms=lap_time_ms,
            samples=samples,
        )

    def update(
        self,
        *,
        frame: TelemetryFrame,
        graphics: ACGraphicsSnapshot,
    ) -> LapTrace | None:
        completed_laps = max(
            0,
            graphics.completed_laps,
        )

        progress = self._progress(
            graphics
        )

        lap_elapsed_seconds = (
            self._lap_elapsed_seconds(
                graphics
            )
        )

        previous_completed_laps = (
            self._previous_completed_laps
        )

        if previous_completed_laps is None:
            self._previous_completed_laps = (
                completed_laps
            )

            if self._can_start_immediately(
                progress=progress,
                lap_elapsed_seconds=(
                    lap_elapsed_seconds
                ),
            ):
                self._start_trace(
                    frame=frame,
                    lap_number=(
                        completed_laps + 1
                    ),
                )

                self._append_sample(
                    frame=frame,
                    graphics=graphics,
                )

            return None

        if (
            completed_laps
            < previous_completed_laps
        ):
            self.reset()

            self._previous_completed_laps = (
                completed_laps
            )

            if self._can_start_immediately(
                progress=progress,
                lap_elapsed_seconds=(
                    lap_elapsed_seconds
                ),
            ):
                self._start_trace(
                    frame=frame,
                    lap_number=(
                        completed_laps + 1
                    ),
                )

                self._append_sample(
                    frame=frame,
                    graphics=graphics,
                )

            return None

        if (
            completed_laps
            > previous_completed_laps
        ):
            completed_trace = (
                self._finish_trace(
                    lap_time_ms=(
                        graphics.last_time_ms
                    )
                )
            )

            self._start_trace(
                frame=frame,
                lap_number=(
                    completed_laps + 1
                ),
            )

            self._append_sample(
                frame=frame,
                graphics=graphics,
            )

            self._previous_completed_laps = (
                completed_laps
            )

            return completed_trace

        if self._recording:
            self._append_sample(
                frame=frame,
                graphics=graphics,
            )

        self._previous_completed_laps = (
            completed_laps
        )

        return None