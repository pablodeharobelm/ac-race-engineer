from pydantic import BaseModel


class SuspensionWheelAnalysis(BaseModel):
    average_travel_mm: float
    maximum_travel_mm: float

    average_load_n: float
    maximum_load_n: float
    minimum_load_n: float

    bottoming_event_count: int


class SuspensionAnalysisReport(BaseModel):
    session_id: str
    car_id: str
    track_id: str

    sample_count: int

    average_front_travel_mm: float
    average_rear_travel_mm: float

    front_rear_travel_delta_mm: float

    average_left_load_n: float
    average_right_load_n: float

    left_right_load_delta_n: float

    total_bottoming_events: int

    wheels: dict[str, SuspensionWheelAnalysis]

