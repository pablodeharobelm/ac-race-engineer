from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from ac_race_engineer.analysis.brake_models import (
    BrakeAnalysisReport,
    BrakeWheelAnalysis,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
    WheelTelemetry,
)


@dataclass
class _BrakeWheelAccumulator:
    window_size: int

    sample_count: int = 0

    temperature_sum: float = 0.0
    peak_temperature: float = float("-inf")

    initial_temperatures: list[float] = field(
        default_factory=list
    )

    final_temperatures: deque[float] = field(
        default_factory=deque
    )

    def add(
        self,
        wheel: WheelTelemetry,
    ) -> None:

        temperature = wheel.brake_temp_c

        self.sample_count += 1

        self.temperature_sum += temperature

        self.peak_temperature = max(
            self.peak_temperature,
            temperature,
        )

        if len(self.initial_temperatures) < self.window_size:
            self.initial_temperatures.append(
                temperature
            )

        if len(self.final_temperatures) >= self.window_size:
            self.final_temperatures.popleft()

        self.final_temperatures.append(
            temperature
        )

    def build(self) -> BrakeWheelAnalysis:

        if self.sample_count == 0:
            raise ValueError(
                "Cannot analyse brake without samples"
            )

        average_temperature = (
            self.temperature_sum
            / self.sample_count
        )

        starting_temperature = (
            sum(self.initial_temperatures)
            / len(self.initial_temperatures)
        )

        ending_temperature = (
            sum(self.final_temperatures)
            / len(self.final_temperatures)
        )

        return BrakeWheelAnalysis(
            average_temperature_c=average_temperature,
            peak_temperature_c=self.peak_temperature,
            starting_temperature_c=starting_temperature,
            ending_temperature_c=ending_temperature,
            temperature_gain_c=(
                ending_temperature
                - starting_temperature
            ),
        )


class BrakeAnalyzer:

    def __init__(
        self,
        window_size: int = 20,
        brake_threshold: float = 0.1,
    ):

        if window_size <= 0:
            raise ValueError(
                "window_size must be greater than 0"
            )

        if not 0.0 <= brake_threshold <= 1.0:
            raise ValueError(
                "brake_threshold must be between 0 and 1"
            )

        self.window_size = window_size
        self.brake_threshold = brake_threshold

    def analyze(
        self,
        session_file: str | Path,
    ) -> BrakeAnalysisReport:

        path = Path(session_file)

        if not path.exists():
            raise FileNotFoundError(path)

        first_frame: TelemetryFrame | None = None
        previous_frame: TelemetryFrame | None = None

        accumulators: dict[
            str,
            _BrakeWheelAccumulator,
        ] = {}

        sample_count = 0

        braking_event_count = 0
        currently_braking = False

        current_event_start: float | None = None

        braking_event_durations: list[float] = []

        maximum_brake_input = 0.0

        brake_input_sum = 0.0
        brake_input_samples = 0

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                frame = (
                    TelemetryFrame.model_validate_json(
                        line
                    )
                )

                if first_frame is None:

                    first_frame = frame

                    accumulators = {
                        position: _BrakeWheelAccumulator(
                            window_size=self.window_size
                        )
                        for position in frame.wheels
                    }

                self._validate_session(
                    first_frame=first_frame,
                    frame=frame,
                )

                sample_count += 1

                brake_input = frame.vehicle.brake

                maximum_brake_input = max(
                    maximum_brake_input,
                    brake_input,
                )

                is_braking = (
                    brake_input
                    >= self.brake_threshold
                )

                if is_braking:

                    brake_input_sum += brake_input
                    brake_input_samples += 1

                    if not currently_braking:

                        braking_event_count += 1
                        currently_braking = True

                        current_event_start = (
                            frame.elapsed_seconds
                        )

                elif currently_braking:

                    if current_event_start is not None:

                        duration = (
                            frame.elapsed_seconds
                            - current_event_start
                        )

                        braking_event_durations.append(
                            duration
                        )

                    currently_braking = False
                    current_event_start = None

                for position, wheel in frame.wheels.items():

                    accumulators[position].add(
                        wheel
                    )

                previous_frame = frame

        if first_frame is None:
            raise ValueError(
                "Session contains no telemetry"
            )

        if (
            currently_braking
            and current_event_start is not None
            and previous_frame is not None
        ):

            duration = (
                previous_frame.elapsed_seconds
                - current_event_start
            )

            braking_event_durations.append(
                duration
            )

        wheels = {
            position: accumulator.build()
            for position, accumulator
            in accumulators.items()
        }

        front_average = (
            wheels["FL"].average_temperature_c
            + wheels["FR"].average_temperature_c
        ) / 2

        rear_average = (
            wheels["RL"].average_temperature_c
            + wheels["RR"].average_temperature_c
        ) / 2

        if brake_input_samples > 0:

            average_brake_input = (
                brake_input_sum
                / brake_input_samples
            )

        else:
            average_brake_input = 0.0

        if braking_event_durations:

            average_event_duration = (
                sum(braking_event_durations)
                / len(braking_event_durations)
            )

        else:
            average_event_duration = 0.0

        return BrakeAnalysisReport(
            session_id=first_frame.session_id,
            car_id=first_frame.car_id,
            track_id=first_frame.track_id,
            sample_count=sample_count,
            braking_event_count=braking_event_count,
            maximum_brake_input=maximum_brake_input,
            average_brake_input_during_events=average_brake_input,
            average_braking_event_duration_seconds=(
                average_event_duration
            ),
            average_front_temperature_c=front_average,
            average_rear_temperature_c=rear_average,
            front_rear_temperature_delta_c=(
                front_average
                - rear_average
            ),
            wheels=wheels,
        )

    @staticmethod
    def _validate_session(
        first_frame: TelemetryFrame,
        frame: TelemetryFrame,
    ) -> None:

        if frame.session_id != first_frame.session_id:
            raise ValueError(
                "Session contains multiple session IDs"
            )

        if frame.car_id != first_frame.car_id:
            raise ValueError(
                "Session contains multiple cars"
            )

        if frame.track_id != first_frame.track_id:
            raise ValueError(
                "Session contains multiple tracks"
            )