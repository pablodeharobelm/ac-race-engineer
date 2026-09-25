from pathlib import Path

from ac_race_engineer.analysis.dynamics_models import (
    VehicleDynamicsReport,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)


class VehicleDynamicsAnalyzer:

    def __init__(
        self,
        minimum_cornering_g: float = 0.3,
        balance_threshold_deg: float = 0.5,
    ):

        if minimum_cornering_g < 0:
            raise ValueError(
                "minimum_cornering_g must be greater than or equal to 0"
            )

        if balance_threshold_deg < 0:
            raise ValueError(
                "balance_threshold_deg must be greater than or equal to 0"
            )

        self.minimum_cornering_g = minimum_cornering_g
        self.balance_threshold_deg = balance_threshold_deg

    def analyze(
        self,
        session_file: str | Path,
    ) -> VehicleDynamicsReport:

        path = Path(session_file)

        if not path.exists():
            raise FileNotFoundError(path)

        first_frame: TelemetryFrame | None = None

        sample_count = 0
        cornering_sample_count = 0

        maximum_lateral_g = 0.0
        maximum_acceleration_g = 0.0
        maximum_braking_g = 0.0

        steering_sum = 0.0
        maximum_steering = 0.0

        front_slip_sum = 0.0
        rear_slip_sum = 0.0

        front_limited_samples = 0
        rear_limited_samples = 0
        neutral_samples = 0

        front_limited_events = 0
        rear_limited_events = 0

        previous_balance_state = "neutral"

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

                    self._validate_wheel_configuration(
                        frame
                    )

                self._validate_session(
                    first_frame=first_frame,
                    frame=frame,
                )

                sample_count += 1

                lateral_g = abs(
                    frame.vehicle.lateral_g
                )

                longitudinal_g = (
                    frame.vehicle.longitudinal_g
                )

                steering = abs(
                    frame.vehicle.steering_angle_deg
                )

                maximum_lateral_g = max(
                    maximum_lateral_g,
                    lateral_g,
                )

                maximum_acceleration_g = max(
                    maximum_acceleration_g,
                    longitudinal_g,
                )

                maximum_braking_g = max(
                    maximum_braking_g,
                    max(0.0, -longitudinal_g),
                )

                steering_sum += steering

                maximum_steering = max(
                    maximum_steering,
                    steering,
                )

                if lateral_g < self.minimum_cornering_g:
                    previous_balance_state = "neutral"
                    continue

                cornering_sample_count += 1

                front_slip = (
                    abs(
                        frame.wheels[
                            "FL"
                        ].slip_angle_deg
                    )
                    + abs(
                        frame.wheels[
                            "FR"
                        ].slip_angle_deg
                    )
                ) / 2

                rear_slip = (
                    abs(
                        frame.wheels[
                            "RL"
                        ].slip_angle_deg
                    )
                    + abs(
                        frame.wheels[
                            "RR"
                        ].slip_angle_deg
                    )
                ) / 2

                front_slip_sum += front_slip
                rear_slip_sum += rear_slip

                slip_delta = (
                    front_slip
                    - rear_slip
                )

                if (
                    slip_delta
                    > self.balance_threshold_deg
                ):

                    current_state = "front_limited"

                    front_limited_samples += 1

                    if (
                        previous_balance_state
                        != "front_limited"
                    ):
                        front_limited_events += 1

                elif (
                    slip_delta
                    < -self.balance_threshold_deg
                ):

                    current_state = "rear_limited"

                    rear_limited_samples += 1

                    if (
                        previous_balance_state
                        != "rear_limited"
                    ):
                        rear_limited_events += 1

                else:

                    current_state = "neutral"

                    neutral_samples += 1

                previous_balance_state = current_state

        if first_frame is None:
            raise ValueError(
                "Session contains no telemetry"
            )

        average_steering = (
            steering_sum
            / sample_count
        )

        if cornering_sample_count > 0:

            average_front_slip = (
                front_slip_sum
                / cornering_sample_count
            )

            average_rear_slip = (
                rear_slip_sum
                / cornering_sample_count
            )

            front_percentage = (
                front_limited_samples
                / cornering_sample_count
                * 100
            )

            rear_percentage = (
                rear_limited_samples
                / cornering_sample_count
                * 100
            )

            neutral_percentage = (
                neutral_samples
                / cornering_sample_count
                * 100
            )

        else:

            average_front_slip = 0.0
            average_rear_slip = 0.0

            front_percentage = 0.0
            rear_percentage = 0.0
            neutral_percentage = 0.0

        return VehicleDynamicsReport(
            session_id=first_frame.session_id,
            car_id=first_frame.car_id,
            track_id=first_frame.track_id,
            sample_count=sample_count,
            cornering_sample_count=(
                cornering_sample_count
            ),
            maximum_lateral_g=(
                maximum_lateral_g
            ),
            maximum_acceleration_g=(
                maximum_acceleration_g
            ),
            maximum_braking_g=(
                maximum_braking_g
            ),
            average_absolute_steering_deg=(
                average_steering
            ),
            maximum_absolute_steering_deg=(
                maximum_steering
            ),
            average_front_slip_angle_deg=(
                average_front_slip
            ),
            average_rear_slip_angle_deg=(
                average_rear_slip
            ),
            front_rear_slip_delta_deg=(
                average_front_slip
                - average_rear_slip
            ),
            front_limited_percentage=(
                front_percentage
            ),
            rear_limited_percentage=(
                rear_percentage
            ),
            neutral_balance_percentage=(
                neutral_percentage
            ),
            front_limited_event_count=(
                front_limited_events
            ),
            rear_limited_event_count=(
                rear_limited_events
            ),
        )

    @staticmethod
    def _validate_wheel_configuration(
        frame: TelemetryFrame,
    ) -> None:

        required_wheels = {
            "FL",
            "FR",
            "RL",
            "RR",
        }

        if not required_wheels.issubset(
            frame.wheels
        ):
            raise ValueError(
                "Vehicle dynamics analysis requires FL, FR, RL and RR wheels"
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

