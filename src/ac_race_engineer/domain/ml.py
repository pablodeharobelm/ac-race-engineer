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