from datetime import datetime

from pydantic import BaseModel


class MLDatasetBuildResult(BaseModel):
    dataset_id: str
    created_at: datetime

    car_id: str
    parameter: str

    row_count: int
    sweep_count: int

    seeds: list[int]

    csv_file: str
    parquet_file: str

class MLTrainingResult(BaseModel):
    model_id: str
    created_at: datetime

    target: str
    features: list[str]

    train_rows: int
    test_rows: int

    train_seeds: list[int]
    test_seeds: list[int]

    mae: float
    rmse: float
    r2: float

    coefficient: float
    intercept: float

    model_file: str
    report_file: str

class MLPredictionResult(BaseModel):
    target: str

    features: dict[str, float]

    prediction: float


class MLModelEvaluationResult(BaseModel):
    model_file: str
    dataset_file: str

    test_rows: int
    test_seeds: list[int]

    mae: float
    rmse: float
    r2: float

    actual_vs_predicted_plot: str
    residual_plot: str