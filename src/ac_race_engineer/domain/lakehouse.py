from typing import Literal

from pydantic import BaseModel


class BronzeIngestionResult(BaseModel):
    session_id: str

    row_count: int

    output_file: str

    status: Literal[
        "written",
        "skipped",
    ]

    partition_date: str
    car_id: str
    track_id: str

class SilverProcessingResult(BaseModel):
    session_id: str

    input_rows: int
    output_rows: int

    duplicate_rows_removed: int
    quarantined_rows: int

    output_file: str
    quarantine_file: str | None
    manifest_file: str

    source_checksum: str

    status: Literal[
        "written",
        "skipped",
    ]

    partition_date: str
    car_id: str
    track_id: str

class GoldAggregationResult(BaseModel):
    session_id: str

    source_rows: int
    output_rows: int

    output_file: str
    manifest_file: str

    source_checksum: str

    status: Literal[
        "written",
        "skipped",
    ]

    partition_date: str
    car_id: str
    track_id: str

class LakehousePipelineResult(BaseModel):
    session_id: str

    bronze: BronzeIngestionResult
    silver: SilverProcessingResult
    gold: GoldAggregationResult

    status: Literal[
        "completed",
    ]

class SparkSilverProcessingResult(BaseModel):
    session_id: str

    input_rows: int
    output_rows: int

    duplicate_rows_removed: int
    quarantined_rows: int

    output_path: str
    quarantine_path: str | None
    manifest_file: str

    source_checksum: str

    status: Literal[
        "written",
        "skipped",
    ]

    partition_date: str
    car_id: str
    track_id: str

    spark_version: str

class SparkSQLSessionSummary(BaseModel):
    session_id: str
    car_id: str
    track_id: str

    sample_count: int
    duration_seconds: float

    maximum_speed_kmh: float
    average_speed_kmh: float

    average_front_pressure_psi: float
    average_rear_pressure_psi: float

    average_front_core_temp_c: float
    average_rear_core_temp_c: float

    average_front_brake_temp_c: float
    average_rear_brake_temp_c: float

    average_front_slip_angle_deg: float
    average_rear_slip_angle_deg: float

    valid_row_percentage: float


class SilverParityMetric(BaseModel):
    metric: str

    pandas_value: float
    spark_value: float

    absolute_difference: float
    within_tolerance: bool


class SilverParityReport(BaseModel):
    session_id: str

    pandas_rows: int
    spark_rows: int

    row_count_match: bool
    sample_index_match: bool

    tolerance: float

    metrics: list[SilverParityMetric]

    max_absolute_difference: float

    all_metrics_match: bool
    parity_passed: bool