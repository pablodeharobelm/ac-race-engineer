from pydantic import BaseModel


class WheelSessionSummary(BaseModel):
    average_pressure_psi: float

    average_core_temp_c: float
    maximum_core_temp_c: float

    average_brake_temp_c: float
    maximum_brake_temp_c: float

    average_load_n: float

    maximum_slip_ratio: float
    maximum_slip_angle_deg: float

    maximum_suspension_travel_mm: float


class SessionSummary(BaseModel):
    session_id: str

    car_id: str
    track_id: str

    sample_count: int
    duration_seconds: float

    maximum_speed_kmh: float

    maximum_lateral_g: float
    maximum_braking_g: float

    fuel_used_l: float

    wheels: dict[str, WheelSessionSummary]