from pydantic import BaseModel


class MLRunAnalyticsReport(BaseModel):
    run_count: int

    model_names: list[str]

    average_mae: float
    average_rmse: float
    average_r2: float

    minimum_mae: float
    maximum_r2: float

    dataset_file_count: int