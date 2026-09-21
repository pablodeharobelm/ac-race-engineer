import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SetupValue(BaseModel):
    parameter: str
    value: float


class CarSetup(BaseModel):
    setup_id: str = Field(
        default_factory=lambda: str(
            uuid.uuid4()
        )
    )

    car_id: str

    name: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )

    values: dict[str, float]


class SetupChange(BaseModel):
    parameter: str

    previous_value: float
    new_value: float

    delta: float


class SetupComparison(BaseModel):
    setup_a_id: str
    setup_b_id: str

    changes: list[SetupChange]