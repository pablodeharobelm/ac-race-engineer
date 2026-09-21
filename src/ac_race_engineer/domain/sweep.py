from datetime import datetime

from pydantic import BaseModel


class SweepPoint(BaseModel):
    parameter_value: float
    experiment_id: str

    front_pressure_psi: float
    rear_pressure_psi: float

    front_core_temperature_c: float
    rear_core_temperature_c: float

    front_brake_temperature_c: float
    rear_brake_temperature_c: float

    front_suspension_travel_mm: float
    rear_suspension_travel_mm: float

    front_slip_angle_deg: float
    rear_slip_angle_deg: float

    front_limited_percentage: float
    rear_limited_percentage: float

    maximum_lateral_g: float


class ParameterSweepResult(BaseModel):
    sweep_id: str
    created_at: datetime

    car_id: str

    parameter: str
    baseline_value: float

    seed: int
    hz: int
    sample_count: int

    points: list[SweepPoint]