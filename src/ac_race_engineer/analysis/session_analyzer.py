from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ac_race_engineer.analysis.models import (
    SessionSummary,
    WheelSessionSummary,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
    WheelTelemetry,
)


@dataclass
class _WheelAccumulator:
    sample_count: int = 0

    pressure_sum: float = 0.0

    core_temp_sum: float = 0.0
    maximum_core_temp: float = 0.0

    brake_temp_sum: float = 0.0
    maximum_brake_temp: float = 0.0

    load_sum: float = 0.0

    maximum_slip_ratio: float = 0.0
    maximum_slip_angle: float = 0.0

    maximum_suspension_travel: float = 0.0

    def add(self, wheel: WheelTelemetry) -> None:
        self.sample_count += 1

        self.pressure_sum += wheel.pressure_psi

        self.core_temp_sum += wheel.tyre_temp_core_c
        self.maximum_core_temp = max(
            self.maximum_core_temp,
            wheel.tyre_temp_core_c,
        )

        self.brake_temp_sum += wheel.brake_temp_c
        self.maximum_brake_temp = max(
            self.maximum_brake_temp,
            wheel.brake_temp_c,
        )

        self.load_sum += wheel.load_n

        self.maximum_slip_ratio = max(
            self.maximum_slip_ratio,
            abs(wheel.slip_ratio),
        )

        self.maximum_slip_angle = max(
            self.maximum_slip_angle,
            abs(wheel.slip_angle_deg),
        )

        self.maximum_suspension_travel = max(
            self.maximum_suspension_travel,
            wheel.suspension_travel_mm,
        )

    def build_summary(self) -> WheelSessionSummary:
        if self.sample_count == 0:
            raise ValueError("Cannot summarize wheel without samples")

        return WheelSessionSummary(
            average_pressure_psi=self.pressure_sum / self.sample_count,
            average_core_temp_c=self.core_temp_sum / self.sample_count,
            maximum_core_temp_c=self.maximum_core_temp,
            average_brake_temp_c=self.brake_temp_sum / self.sample_count,
            maximum_brake_temp_c=self.maximum_brake_temp,
            average_load_n=self.load_sum / self.sample_count,
            maximum_slip_ratio=self.maximum_slip_ratio,
            maximum_slip_angle_deg=self.maximum_slip_angle,
            maximum_suspension_travel_mm=self.maximum_suspension_travel,
        )


class SessionAnalyzer:
    def analyze(
        self,
        session_file: str | Path,
    ) -> SessionSummary:

        path = Path(session_file)

        if not path.exists():
            raise FileNotFoundError(path)

        first_frame: TelemetryFrame | None = None
        last_frame: TelemetryFrame | None = None

        sample_count = 0

        maximum_speed = 0.0
        maximum_lateral_g = 0.0
        minimum_longitudinal_g = 0.0

        wheel_accumulators: dict[str, _WheelAccumulator] = {}

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line_number, line in enumerate(
                file,
                start=1,
            ):
                line = line.strip()

                if not line:
                    continue

                try:
                    frame = TelemetryFrame.model_validate_json(
                        line
                    )
                except ValidationError as exc:
                    raise ValueError(
                        f"Invalid telemetry data on line {line_number}"
                    ) from exc

                if first_frame is None:
                    first_frame = frame

                    wheel_accumulators = {
                        position: _WheelAccumulator()
                        for position in frame.wheels
                    }

                else:
                    self._validate_frame(
                        first_frame=first_frame,
                        frame=frame,
                    )

                sample_count += 1
                last_frame = frame

                maximum_speed = max(
                    maximum_speed,
                    frame.vehicle.speed_kmh,
                )

                maximum_lateral_g = max(
                    maximum_lateral_g,
                    abs(frame.vehicle.lateral_g),
                )

                minimum_longitudinal_g = min(
                    minimum_longitudinal_g,
                    frame.vehicle.longitudinal_g,
                )

                for position, wheel in frame.wheels.items():
                    wheel_accumulators[position].add(
                        wheel
                    )

        if first_frame is None or last_frame is None:
            raise ValueError(
                "Session file contains no telemetry frames"
            )

        duration = (
            last_frame.elapsed_seconds
            - first_frame.elapsed_seconds
        )

        fuel_used = max(
            0.0,
            first_frame.vehicle.fuel_l
            - last_frame.vehicle.fuel_l,
        )

        maximum_braking_g = abs(
            min(
                0.0,
                minimum_longitudinal_g,
            )
        )

        wheel_summaries = {
            position: accumulator.build_summary()
            for position, accumulator
            in wheel_accumulators.items()
        }

        return SessionSummary(
            session_id=first_frame.session_id,
            car_id=first_frame.car_id,
            track_id=first_frame.track_id,
            sample_count=sample_count,
            duration_seconds=duration,
            maximum_speed_kmh=maximum_speed,
            maximum_lateral_g=maximum_lateral_g,
            maximum_braking_g=maximum_braking_g,
            fuel_used_l=fuel_used,
            wheels=wheel_summaries,
        )

    @staticmethod
    def _validate_frame(
        first_frame: TelemetryFrame,
        frame: TelemetryFrame,
    ) -> None:

        if frame.session_id != first_frame.session_id:
            raise ValueError(
                "Session contains frames from different sessions"
            )

        if frame.car_id != first_frame.car_id:
            raise ValueError(
                "Session contains multiple cars"
            )

        if frame.track_id != first_frame.track_id:
            raise ValueError(
                "Session contains multiple tracks"
            )

        if frame.wheels.keys() != first_frame.wheels.keys():
            raise ValueError(
                "Wheel configuration changed during session"
            )

