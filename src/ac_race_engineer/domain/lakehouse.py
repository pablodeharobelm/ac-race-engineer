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