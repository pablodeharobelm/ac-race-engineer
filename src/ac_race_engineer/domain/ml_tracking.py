from datetime import datetime

from pydantic import BaseModel


class MLRunMetrics(BaseModel):
    mae: float
    rmse: float
    r2: float


class MLRunRecord(BaseModel):
    run_id: str
    created_at: datetime

    model_name: str
    model_id: str

    dataset_file: str
    model_file: str
    report_file: str

    target: str
    features: list[str]

    train_rows: int
    test_rows: int

    train_seeds: list[int]
    test_seeds: list[int]

    metrics: MLRunMetrics

    parameters: dict[
        str,
        str | int | float | bool,
    ]

    library_versions: dict[str, str]