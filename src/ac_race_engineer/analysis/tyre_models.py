from pydantic import BaseModel


class TyreWheelAnalysis(BaseModel):
    average_pressure_psi: float
    starting_pressure_psi: float
    ending_pressure_psi: float
    pressure_gain_psi: float

    average_inner_temp_c: float
    average_middle_temp_c: float
    average_outer_temp_c: float
    average_core_temp_c: float

    peak_core_temp_c: float

    inner_outer_delta_c: float
    thermal_spread_c: float

    starting_core_temp_c: float
    ending_core_temp_c: float
    warmup_gain_c: float


class TyreAnalysisReport(BaseModel):
    session_id: str
    car_id: str
    track_id: str

    sample_count: int

    wheels: dict[str, TyreWheelAnalysis]

