from dataclasses import dataclass
from pathlib import Path

from ac_race_engineer.analysis.suspension_models import (
    SuspensionAnalysisReport,
    SuspensionWheelAnalysis,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
    WheelTelemetry,
)


@dataclass
class _SuspensionAccumulator:
    sample_count: int = 0

    travel_sum: float = 0.0
    maximum_travel: float = float("-inf")

    load_sum: float = 0.0
    maximum_load: float = float("-inf")
    minimum_load: float = float("inf")

    bottoming_event_count: int = 0

    was_bottoming: bool = False

    def add(
        self,
        wheel: WheelTelemetry,
        bottoming_threshold_mm: float,
    ) -> None:

        self.sample_count += 1

        travel = wheel.suspension_travel_mm
        load = wheel.load_n

        self.travel_sum += travel

        self.maximum_travel = max(
            self.maximum_travel,
            travel,
        )

        self.load_sum += load

        self.maximum_load = max(
            self.maximum_load,
            load,
        )

        self.minimum_load = min(
            self.minimum_load,
            load,
        )

        is_bottoming = (
            travel >= bottoming_threshold_mm
        )

        if is_bottoming and not self.was_bottoming:
            self.bottoming_event_count += 1

        self.was_bottoming = is_bottoming

    def build(self) -> SuspensionWheelAnalysis:

        if self.sample_count == 0:
            raise ValueError(
                "Cannot analyse suspension without samples"
            )

        return SuspensionWheelAnalysis(
            average_travel_mm=(
                self.travel_sum
                / self.sample_count
            ),
            maximum_travel_mm=self.maximum_travel,
            average_load_n=(
                self.load_sum
                / self.sample_count
            ),
            maximum_load_n=self.maximum_load,
            minimum_load_n=self.minimum_load,
            bottoming_event_count=(
                self.bottoming_event_count
            ),
        )


class SuspensionAnalyzer:

    def __init__(
        self,
        bottoming_threshold_mm: float = 75.0,
    ):

        if bottoming_threshold_mm <= 0:
            raise ValueError(
                "bottoming_threshold_mm must be greater than 0"
            )

        self.bottoming_threshold_mm = (
            bottoming_threshold_mm
        )

    def analyze(
        self,
        session_file: str | Path,
    ) -> SuspensionAnalysisReport:

        path = Path(session_file)

        if not path.exists():
            raise FileNotFoundError(path)

        first_frame: TelemetryFrame | None = None

        accumulators: dict[
            str,
            _SuspensionAccumulator,
        ] = {}

        sample_count = 0

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
                        position: _SuspensionAccumulator()
                        for position in frame.wheels
                    }

                self._validate_session(
                    first_frame=first_frame,
                    frame=frame,
                )

                for position, wheel in frame.wheels.items():

                    accumulators[position].add(
                        wheel=wheel,
                        bottoming_threshold_mm=(
                            self.bottoming_threshold_mm
                        ),
                    )

                sample_count += 1

        if first_frame is None:
            raise ValueError(
                "Session contains no telemetry"
            )

        wheels = {
            position: accumulator.build()
            for position, accumulator
            in accumulators.items()
        }

        front_average_travel = (
            wheels["FL"].average_travel_mm
            + wheels["FR"].average_travel_mm
        ) / 2

        rear_average_travel = (
            wheels["RL"].average_travel_mm
            + wheels["RR"].average_travel_mm
        ) / 2

        left_average_load = (
            wheels["FL"].average_load_n
            + wheels["RL"].average_load_n
        ) / 2

        right_average_load = (
            wheels["FR"].average_load_n
            + wheels["RR"].average_load_n
        ) / 2

        total_bottoming_events = sum(
            wheel.bottoming_event_count
            for wheel in wheels.values()
        )

        return SuspensionAnalysisReport(
            session_id=first_frame.session_id,
            car_id=first_frame.car_id,
            track_id=first_frame.track_id,
            sample_count=sample_count,
            average_front_travel_mm=front_average_travel,
            average_rear_travel_mm=rear_average_travel,
            front_rear_travel_delta_mm=(
                front_average_travel
                - rear_average_travel
            ),
            average_left_load_n=left_average_load,
            average_right_load_n=right_average_load,
            left_right_load_delta_n=(
                left_average_load
                - right_average_load
            ),
            total_bottoming_events=(
                total_bottoming_events
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

