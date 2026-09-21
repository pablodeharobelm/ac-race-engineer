import math
import random
import uuid
from datetime import UTC, datetime

from ac_race_engineer.telemetry.models import (
    EnvironmentTelemetry,
    TelemetryFrame,
    VehicleTelemetry,
    WheelTelemetry,
)
from ac_race_engineer.telemetry.source import TelemetrySource


class SimulatorSource(TelemetrySource):

    def __init__(self, hz: int = 20):
        self.hz = hz
        self.delta_time = 1 / hz

        self.elapsed_seconds = 0.0
        self.sample_index = 0

        self.session_id = str(uuid.uuid4())

        self.car_id = "mazda_mx5_cup"
        self.track_id = "development_track"

        self.fuel_l = 40.0

    @property
    def source_name(self) -> str:
        return "simulator"

    def _generate_wheel(
        self,
        position: str,
        speed_kmh: float,
        lateral_g: float,
        brake: float,
    ) -> WheelTelemetry:

        is_front = position.startswith("F")
        is_left = position.endswith("L")

        lateral_load_transfer = lateral_g * 700

        if is_left:
            lateral_load_transfer *= -1

        load_n = 3000 + lateral_load_transfer

        if is_front:
            load_n += brake * 1000
        else:
            load_n -= brake * 500

        load_n = max(500, load_n)

        core_temp = (
            75
            + abs(lateral_g) * 6
            + brake * 3
            + random.uniform(-1, 1)
        )

        camber_effect = 4 if is_front else 3

        temp_inner = core_temp + camber_effect
        temp_middle = core_temp
        temp_outer = core_temp - camber_effect

        pressure = (
            26
            + (core_temp - 75) * 0.025
            + random.uniform(-0.1, 0.1)
        )

        slip_ratio = random.uniform(0.01, 0.03)

        if brake > 0.8:
            slip_ratio += random.uniform(0.02, 0.08)

        slip_angle_deg = (
            abs(lateral_g)
            * random.uniform(2.5, 4.5)
        )

        brake_temp_c = (
            200
            + brake * 400
            + random.uniform(-10, 10)
        )

        suspension_travel_mm = (
            40
            + load_n / 120
            + random.uniform(-2, 2)
        )

        wheel_speed_kmh = speed_kmh * random.uniform(
            0.997,
            1.003,
        )

        return WheelTelemetry(
            pressure_psi=pressure,
            tyre_temp_inner_c=temp_inner,
            tyre_temp_middle_c=temp_middle,
            tyre_temp_outer_c=temp_outer,
            tyre_temp_core_c=core_temp,
            brake_temp_c=brake_temp_c,
            wheel_speed_kmh=wheel_speed_kmh,
            load_n=load_n,
            slip_ratio=slip_ratio,
            slip_angle_deg=slip_angle_deg,
            suspension_travel_mm=suspension_travel_mm,
        )

    def read_frame(self) -> TelemetryFrame:

        self.elapsed_seconds += self.delta_time
        self.sample_index += 1

        phase = self.elapsed_seconds % 20

        speed_kmh = (
            130
            + math.sin(self.elapsed_seconds * 0.4) * 70
        )

        speed_kmh = max(40, speed_kmh)

        throttle = (
            0.6
            + math.sin(self.elapsed_seconds * 0.5) * 0.4
        )

        throttle = max(
            0.0,
            min(1.0, throttle),
        )

        brake = 0.0

        if 8 < phase < 10:
            brake = min(
                1.0,
                phase - 8,
            )

            throttle *= 0.1

        steering_angle_deg = (
            math.sin(self.elapsed_seconds * 0.7)
            * 25
        )

        lateral_g = (
            steering_angle_deg
            / 25
            * speed_kmh
            / 150
            * 1.3
        )

        longitudinal_g = (
            throttle * 0.45
            - brake * 1.3
        )

        rpm = int(
            2500
            + speed_kmh * 30
        )

        rpm = min(
            rpm,
            7500,
        )

        gear = int(speed_kmh / 35)

        gear = max(
            1,
            min(6, gear),
        )

        self.fuel_l -= (
            throttle
            * self.delta_time
            * 0.003
        )

        vehicle = VehicleTelemetry(
            speed_kmh=speed_kmh,
            rpm=rpm,
            gear=gear,
            throttle=throttle,
            brake=brake,
            clutch=0.0,
            steering_angle_deg=steering_angle_deg,
            lateral_g=lateral_g,
            longitudinal_g=longitudinal_g,
            fuel_l=self.fuel_l,
            brake_bias=0.64,
            pitch_deg=-longitudinal_g * 1.4,
            roll_deg=lateral_g * 1.7,
            ride_height_front_mm=70 - brake * 5,
            ride_height_rear_mm=75 + brake * 3,
        )

        environment = EnvironmentTelemetry(
            air_temperature_c=24.0,
            track_temperature_c=33.0,
            grip_level=0.97,
        )

        wheels = {
            position: self._generate_wheel(
                position=position,
                speed_kmh=speed_kmh,
                lateral_g=lateral_g,
                brake=brake,
            )
            for position in ["FL", "FR", "RL", "RR"]
        }

        return TelemetryFrame(
            timestamp=datetime.now(UTC),
            session_id=self.session_id,
            sample_index=self.sample_index,
            elapsed_seconds=self.elapsed_seconds,
            car_id=self.car_id,
            track_id=self.track_id,
            vehicle=vehicle,
            environment=environment,
            wheels=wheels,
        )