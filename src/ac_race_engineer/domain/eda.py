from pydantic import BaseModel


class SweepEDAReport(BaseModel):
    parameter: str

    row_count: int

    minimum_parameter_value: float
    maximum_parameter_value: float

    minimum_front_slip_value: float
    minimum_front_slip_angle_deg: float

    correlations: dict[
        str,
        float | None,
    ]

