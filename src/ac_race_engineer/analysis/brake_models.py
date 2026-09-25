from pydantic import BaseModel


class BrakeWheelAnalysis(BaseModel):
    average_temperature_c: float
    peak_temperature_c: float

    starting_temperature_c: float
    ending_temperature_c: float
    temperature_gain_c: float


class BrakeAnalysisReport(BaseModel):
    session_id: str
    car_id: str
    track_id: str

    sample_count: int

    braking_event_count: int

    maximum_brake_input: float
    average_brake_input_during_events: float
    average_braking_event_duration_seconds: float

    average_front_temperature_c: float
    average_rear_temperature_c: float

    front_rear_temperature_delta_c: float

    wheels: dict[str, BrakeWheelAnalysis]

