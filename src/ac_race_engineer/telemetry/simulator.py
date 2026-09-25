import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.telemetry.models import (
    EnvironmentTelemetry,
    TelemetryFrame,
    VehicleTelemetry,
    WheelTelemetry,
)
from ac_race_engineer.telemetry.source import TelemetrySource


@dataclass
class _WheelState:
    tyre_core_temp_c: float = 24.0
    brake_temp_c: float = 80.0
    cold_pressure_psi: float = 24.5


class SimulatorSource(TelemetrySource):

    def __init__(
        self,
        hz: int = 20,
        seed: int | None = None,
        setup: CarSetup | None = None,
    ):
        if hz <= 0:
            raise ValueError(
                "hz must be greater than 0"
            )

        self.hz = hz
        self.delta_time = 1 / hz

        self.random = random.Random(seed)

        self.elapsed_seconds = 0.0
        self.sample_index = 0

        self.session_id = str(uuid.uuid4())

        self.car_id = "mazda_mx5_cup"
        self.track_id = "development_track"

        self.setup = setup

        if (
            setup is not None
            and setup.car_id != self.car_id
        ):
            raise ValueError(
                "Setup does not belong to simulator car"
            )

        self.front_pressure = self._setup_value(
            "front_pressure",
            24.5,
        )

        self.rear_pressure = self._setup_value(
            "rear_pressure",
            24.5,
        )

        self.front_camber = self._setup_value(
            "front_camber",
            -2.5,
        )

        self.rear_camber = self._setup_value(
            "rear_camber",
            -2.0,
        )

        self.brake_bias = self._setup_value(
            "brake_bias",
            0.64,
        )

        self.fuel_l = 40.0
        self.speed_kmh = 80.0

        self.air_temperature_c = 24.0
        self.track_temperature_c = 33.0

        self.wheel_states = {
            "FL": _WheelState(
                cold_pressure_psi=self.front_pressure
            ),
            "FR": _WheelState(
                cold_pressure_psi=self.front_pressure
            ),
            "RL": _WheelState(
                cold_pressure_psi=self.rear_pressure
            ),
            "RR": _WheelState(
                cold_pressure_psi=self.rear_pressure
            ),
        }

    @property
    def source_name(self) -> str:
        return "simulator"

    def _driver_inputs(
        self,
    ) -> tuple[float, float, float]:

        phase = self.elapsed_seconds % 30

        if phase < 6:
            throttle = 0.95
            brake = 0.0
            steering = 2.0

        elif phase < 8:
            throttle = 0.0
            brake = 0.85
            steering = 5.0

        elif phase < 14:
            throttle = 0.45
            brake = 0.0
            steering = 18.0

        elif phase < 19:
            throttle = 0.90
            brake = 0.0
            steering = 3.0

        elif phase < 21:
            throttle = 0.0
            brake = 1.0
            steering = -4.0

        elif phase < 27:
            throttle = 0.35
            brake = 0.0
            steering = -22.0

        else:
            throttle = 1.0
            brake = 0.0
            steering = -3.0

        steering += self.random.uniform(
            -0.5,
            0.5,
        )

        return (
            throttle,
            brake,
            steering,
        )

    def _update_speed(
        self,
        throttle: float,
        brake: float,
    ) -> float:

        speed_mps = (
            self.speed_kmh
            / 3.6
        )

        engine_acceleration = (
            throttle
            * 4.0
        )

        braking_deceleration = (
            brake
            * 10.5
        )

        aerodynamic_drag = (
            speed_mps
            * 0.015
        )

        acceleration = (
            engine_acceleration
            - braking_deceleration
            - aerodynamic_drag
        )

        speed_mps += (
            acceleration
            * self.delta_time
        )

        speed_mps = max(
            10.0,
            min(
                61.0,
                speed_mps,
            ),
        )

        self.speed_kmh = (
            speed_mps
            * 3.6
        )

        return acceleration

    def _generate_wheel(
        self,
        position: str,
        lateral_g: float,
        throttle: float,
        brake: float,
    ) -> WheelTelemetry:

        state = self.wheel_states[
            position
        ]

        is_front = position.startswith("F")
        is_left = position.endswith("L")
        is_rear = not is_front

        lateral_transfer = (
            lateral_g
            * 700
        )

        if is_left:
            lateral_transfer *= -1

        load_n = (
            3000
            + lateral_transfer
        )

        if is_front:
            load_n += (
                brake
                * 1100
            )
        else:
            load_n -= (
                brake
                * 550
            )

        load_n = max(
            500,
            load_n,
        )

        slip_ratio = (
            self.random.uniform(
                0.005,
                0.015,
            )
        )

        if brake > 0.4:
            slip_ratio += (
                brake
                * 0.05
            )

        if (
            is_rear
            and throttle > 0.7
        ):
            slip_ratio += (
                throttle
                * 0.025
            )

        base_slip_angle = (
            abs(lateral_g)
            * 3.0
        )

        ideal_pressure = 24.5

        pressure_error = abs(
            state.cold_pressure_psi
            - ideal_pressure
        )

        pressure_slip_factor = (
            1.0
            + pressure_error * 0.02
        )

        if is_front:
            slip_angle_deg = (
                base_slip_angle
                * 1.05
                * pressure_slip_factor
            )
        else:
            slip_angle_deg = (
                base_slip_angle
                * (
                    0.95
                    + throttle * 0.10
                )
                * pressure_slip_factor
            )

        slip_angle_deg += (
            self.random.uniform(
                -0.15,
                0.15,
            )
        )

        slip_angle_deg = max(
            0.0,
            slip_angle_deg,
        )

        tyre_heat = (
            abs(lateral_g)
            * 1.4
            + slip_ratio * 12
            + brake * 0.3
        )

        tyre_cooling = (
            (
                state.tyre_core_temp_c
                - self.air_temperature_c
            )
            * 0.025
            * (
                0.4
                + self.speed_kmh / 150
            )
        )

        state.tyre_core_temp_c += (
            tyre_heat
            - tyre_cooling
        ) * self.delta_time

        if is_front:
            axle_brake_share = (
                self.brake_bias
            )
        else:
            axle_brake_share = (
                1.0
                - self.brake_bias
            )

        brake_heat = (
            brake
            * (
                self.speed_kmh
                / 100
            )
            * 70
            * (
                axle_brake_share
                / 0.5
            )
        )

        brake_cooling = (
            (
                state.brake_temp_c
                - self.air_temperature_c
            )
            * 0.07
            * (
                0.5
                + self.speed_kmh / 180
            )
        )

        state.brake_temp_c += (
            brake_heat
            - brake_cooling
        ) * self.delta_time

        state.brake_temp_c = max(
            self.air_temperature_c,
            state.brake_temp_c,
        )

        camber_deg = (
            self.front_camber
            if is_front
            else self.rear_camber 
        )

        camber_gradient = (
            abs(camber_deg)
            * 1.6
        )

        temp_inner = (
            state.tyre_core_temp_c
            + camber_gradient
        )

        temp_middle = (
            state.tyre_core_temp_c
        )

        temp_outer = (
            state.tyre_core_temp_c
            - camber_gradient
        )

        pressure_psi = (
            state.cold_pressure_psi
            + (
                state.tyre_core_temp_c
                - self.air_temperature_c
            )
            * 0.03
        )

        suspension_travel_mm = (
            38
            + load_n / 110
            + self.random.uniform(
                -2,
                2,
            )
        )

        if brake > 0.8 and is_front:
            suspension_travel_mm += 5

        wheel_speed_kmh = (
            self.speed_kmh
        )

        if brake > 0:
            wheel_speed_kmh *= (
                1
                - slip_ratio
            )

        elif (
            is_rear
            and throttle > 0.7
        ):
            wheel_speed_kmh *= (
                1
                + slip_ratio
            )

        return WheelTelemetry(
            pressure_psi=pressure_psi,
            tyre_temp_inner_c=temp_inner,
            tyre_temp_middle_c=temp_middle,
            tyre_temp_outer_c=temp_outer,
            tyre_temp_core_c=(
                state.tyre_core_temp_c
            ),
            brake_temp_c=(
                state.brake_temp_c
            ),
            wheel_speed_kmh=(
                wheel_speed_kmh
            ),
            load_n=load_n,
            slip_ratio=slip_ratio,
            slip_angle_deg=(
                slip_angle_deg
            ),
            suspension_travel_mm=(
                suspension_travel_mm
            ),
        )

    def read_frame(
        self,
    ) -> TelemetryFrame:

        self.elapsed_seconds += (
            self.delta_time
        )

        self.sample_index += 1

        throttle, brake, steering = (
            self._driver_inputs()
        )

        acceleration = (
            self._update_speed(
                throttle=throttle,
                brake=brake,
            )
        )

        lateral_g = (
            (
                steering
                / 25
            )
            * (
                self.speed_kmh
                / 150
            )
            * 1.35
        )

        longitudinal_g = (
            acceleration
            / 9.81
        )

        gear = max(
            1,
            min(
                6,
                int(
                    self.speed_kmh
                    / 35
                )
                + 1,
            ),
        )

        rpm = int(
            1800
            + (
                self.speed_kmh
                / gear
            )
            * 115
        )

        rpm = max(
            1500,
            min(
                7500,
                rpm,
            ),
        )

        self.fuel_l -= (
            throttle
            * self.delta_time
            * 0.004
        )

        self.fuel_l = max(
            0.0,
            self.fuel_l,
        )

        vehicle = VehicleTelemetry(
            speed_kmh=self.speed_kmh,
            rpm=rpm,
            gear=gear,
            throttle=throttle,
            brake=brake,
            clutch=0.0,
            steering_angle_deg=steering,
            lateral_g=lateral_g,
            longitudinal_g=longitudinal_g,
            fuel_l=self.fuel_l,
            brake_bias=self.brake_bias,
            pitch_deg=(
                -longitudinal_g
                * 1.5
            ),
            roll_deg=(
                lateral_g
                * 1.8
            ),
            ride_height_front_mm=(
                70
                - brake * 6
            ),
            ride_height_rear_mm=(
                75
                + brake * 3
            ),
        )

        environment = EnvironmentTelemetry(
            air_temperature_c=(
                self.air_temperature_c
            ),
            track_temperature_c=(
                self.track_temperature_c
            ),
            grip_level=0.97,
        )

        wheels = {
            position: self._generate_wheel(
                position=position,
                lateral_g=lateral_g,
                throttle=throttle,
                brake=brake,
            )
            for position in (
                "FL",
                "FR",
                "RL",
                "RR",
            )
        }

        return TelemetryFrame(
            timestamp=datetime.now(UTC),
            session_id=self.session_id,
            sample_index=self.sample_index,
            elapsed_seconds=(
                self.elapsed_seconds
            ),
            car_id=self.car_id,
            track_id=self.track_id,
            vehicle=vehicle,
            environment=environment,
            wheels=wheels,
        )
    def _setup_value(
        self,
        parameter: str,
        default: float,
    ) -> float:

        if self.setup is None:
            return default

        return self.setup.values.get(
            parameter,
            default,
        )

