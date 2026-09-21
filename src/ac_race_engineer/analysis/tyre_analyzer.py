from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from ac_race_engineer.analysis.tyre_models import (
    TyreAnalysisReport,
    TyreWheelAnalysis,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
    WheelTelemetry,
)


@dataclass
class _TyreAccumulator:
    window_size: int

    sample_count: int = 0

    pressure_sum: float = 0.0

    inner_temp_sum: float = 0.0
    middle_temp_sum: float = 0.0
    outer_temp_sum: float = 0.0
    core_temp_sum: float = 0.0

    peak_core_temp: float = float("-inf")

    initial_pressures: list[float] = field(
        default_factory=list
    )

    initial_core_temps: list[float] = field(
        default_factory=list
    )

    final_pressures: deque[float] = field(
        default_factory=deque
    )

    final_core_temps: deque[float] = field(
        default_factory=deque
    )

    def add(
        self,
        wheel: WheelTelemetry,
    ) -> None:

        self.sample_count += 1

        self.pressure_sum += wheel.pressure_psi

        self.inner_temp_sum += wheel.tyre_temp_inner_c
        self.middle_temp_sum += wheel.tyre_temp_middle_c
        self.outer_temp_sum += wheel.tyre_temp_outer_c
        self.core_temp_sum += wheel.tyre_temp_core_c

        self.peak_core_temp = max(
            self.peak_core_temp,
            wheel.tyre_temp_core_c,
        )

        if len(self.initial_pressures) < self.window_size:
            self.initial_pressures.append(
                wheel.pressure_psi
            )

            self.initial_core_temps.append(
                wheel.tyre_temp_core_c
            )

        if len(self.final_pressures) >= self.window_size:
            self.final_pressures.popleft()
            self.final_core_temps.popleft()

        self.final_pressures.append(
            wheel.pressure_psi
        )

        self.final_core_temps.append(
            wheel.tyre_temp_core_c
        )

    def build(self) -> TyreWheelAnalysis:

        if self.sample_count == 0:
            raise ValueError(
                "Cannot analyse tyre without samples"
            )

        average_pressure = (
            self.pressure_sum
            / self.sample_count
        )

        average_inner = (
            self.inner_temp_sum
            / self.sample_count
        )

        average_middle = (
            self.middle_temp_sum
            / self.sample_count
        )

        average_outer = (
            self.outer_temp_sum
            / self.sample_count
        )

        average_core = (
            self.core_temp_sum
            / self.sample_count
        )

        starting_pressure = (
            sum(self.initial_pressures)
            / len(self.initial_pressures)
        )

        ending_pressure = (
            sum(self.final_pressures)
            / len(self.final_pressures)
        )

        starting_core_temp = (
            sum(self.initial_core_temps)
            / len(self.initial_core_temps)
        )

        ending_core_temp = (
            sum(self.final_core_temps)
            / len(self.final_core_temps)
        )

        temperatures = [
            average_inner,
            average_middle,
            average_outer,
        ]

        return TyreWheelAnalysis(
            average_pressure_psi=average_pressure,
            starting_pressure_psi=starting_pressure,
            ending_pressure_psi=ending_pressure,
            pressure_gain_psi=(
                ending_pressure
                - starting_pressure
            ),
            average_inner_temp_c=average_inner,
            average_middle_temp_c=average_middle,
            average_outer_temp_c=average_outer,
            average_core_temp_c=average_core,
            peak_core_temp_c=self.peak_core_temp,
            inner_outer_delta_c=(
                average_inner
                - average_outer
            ),
            thermal_spread_c=(
                max(temperatures)
                - min(temperatures)
            ),
            starting_core_temp_c=starting_core_temp,
            ending_core_temp_c=ending_core_temp,
            warmup_gain_c=(
                ending_core_temp
                - starting_core_temp
            ),
        )


class TyreAnalyzer:

    def __init__(
        self,
        window_size: int = 20,
    ):

        if window_size <= 0:
            raise ValueError(
                "window_size must be greater than 0"
            )

        self.window_size = window_size

    def analyze(
        self,
        session_file: str | Path,
    ) -> TyreAnalysisReport:

        path = Path(session_file)

        if not path.exists():
            raise FileNotFoundError(path)

        first_frame: TelemetryFrame | None = None

        accumulators: dict[
            str,
            _TyreAccumulator,
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
                        position: _TyreAccumulator(
                            window_size=self.window_size
                        )
                        for position in frame.wheels
                    }

                self._validate_session(
                    first_frame=first_frame,
                    frame=frame,
                )

                for position, wheel in frame.wheels.items():

                    accumulators[position].add(
                        wheel
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

        return TyreAnalysisReport(
            session_id=first_frame.session_id,
            car_id=first_frame.car_id,
            track_id=first_frame.track_id,
            sample_count=sample_count,
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