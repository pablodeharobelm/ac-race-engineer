from pydantic import BaseModel


class VehicleDynamicsReport(BaseModel):
    session_id: str
    car_id: str
    track_id: str

    sample_count: int
    cornering_sample_count: int

    maximum_lateral_g: float
    maximum_acceleration_g: float
    maximum_braking_g: float

    average_absolute_steering_deg: float
    maximum_absolute_steering_deg: float

    average_front_slip_angle_deg: float
    average_rear_slip_angle_deg: float

    front_rear_slip_delta_deg: float

    front_limited_percentage: float
    rear_limited_percentage: float
    neutral_balance_percentage: float

    front_limited_event_count: int
    rear_limited_event_count: int

