from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Drivetrain(StrEnum):
    FWD = "FWD"
    RWD = "RWD"
    AWD = "AWD"


class EngineLayout(StrEnum):
    FRONT = "front"
    MID = "mid"
    REAR = "rear"


class SetupParameterDefinition(BaseModel):
    key: str
    display_name: str
    unit: str

    minimum: float
    maximum: float

    step: float | None = None

    @model_validator(mode="after")
    def validate_range(
        self,
    ) -> "SetupParameterDefinition":

        if self.minimum >= self.maximum:
            raise ValueError(
                "minimum must be lower than maximum"
            )

        if self.step is not None and self.step <= 0:
            raise ValueError(
                "step must be greater than 0"
            )

        return self


class CarDefinition(BaseModel):
    car_id: str

    manufacturer: str
    model: str

    drivetrain: Drivetrain
    engine_layout: EngineLayout

    mass_kg: float = Field(gt=0)

    max_rpm: int = Field(gt=0)

    fuel_capacity_l: float = Field(gt=0)

    setup_parameters: dict[
        str,
        SetupParameterDefinition,
    ] = Field(
        default_factory=dict
    )