from pydantic import BaseModel

from ac_race_engineer.domain.setup import SetupComparison


class MetricDelta(BaseModel):
    baseline: float
    candidate: float
    delta: float


class TyreExperimentDelta(BaseModel):
    pressure_psi: MetricDelta
    core_temperature_c: MetricDelta


class BrakeExperimentDelta(BaseModel):
    average_temperature_c: MetricDelta
    peak_temperature_c: MetricDelta


class SuspensionExperimentDelta(BaseModel):
    average_travel_mm: MetricDelta
    average_load_n: MetricDelta


class DynamicsExperimentDelta(BaseModel):
    front_slip_angle_deg: MetricDelta
    rear_slip_angle_deg: MetricDelta

    front_limited_percentage: MetricDelta
    rear_limited_percentage: MetricDelta

    maximum_lateral_g: MetricDelta


class ExperimentComparison(BaseModel):
    car_id: str
    track_id: str

    setup_changes: SetupComparison

    tyres: dict[str, TyreExperimentDelta]
    brakes: dict[str, BrakeExperimentDelta]
    suspension: dict[str, SuspensionExperimentDelta]

    dynamics: DynamicsExperimentDelta