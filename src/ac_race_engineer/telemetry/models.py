from datetime import datetime

from pydantic import BaseModel, Field


class WheelTelemetry(BaseModel):
    pressure_psi: float

    tyre_temp_inner_c: float
    tyre_temp_middle_c: float
    tyre_temp_outer_c: float
    tyre_temp_core_c: float

    brake_temp_c: float

    wheel_speed_kmh: float
    load_n: float

    slip_ratio: float
    slip_angle_deg: float

    suspension_travel_mm: float


class VehicleTelemetry(BaseModel):
    speed_kmh: float
    rpm: int
    gear: int

    throttle: float = Field(ge=0.0, le=1.0)
    brake: float = Field(ge=0.0, le=1.0)
    clutch: float = Field(ge=0.0, le=1.0)

    steering_angle_deg: float

    lateral_g: float
    longitudinal_g: float

    fuel_l: float = Field(ge=0.0)

    brake_bias: float = Field(ge=0.0, le=1.0)

    pitch_deg: float
    roll_deg: float

    ride_height_front_mm: float
    ride_height_rear_mm: float


class EnvironmentTelemetry(BaseModel):
    air_temperature_c: float
    track_temperature_c: float

    grip_level: float = Field(
        ge=0.0,
        le=1.0,
    )


class TelemetryFrame(BaseModel):
    timestamp: datetime

    session_id: str
    sample_index: int = Field(ge=0)

    elapsed_seconds: float = Field(ge=0.0)

    car_id: str
    track_id: str

    vehicle: VehicleTelemetry
    environment: EnvironmentTelemetry

    wheels: dict[str, WheelTelemetry]

