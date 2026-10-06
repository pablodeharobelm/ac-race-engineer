from pathlib import Path
from typing import ClassVar

import pyarrow as pa
import pyarrow.parquet as pq

from ac_race_engineer.telemetry.assetto_corsa.trace import (
    DrivingTraceSample,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_tracker import (
    LapTrace,
)


class LapTraceParquetStore:
    """
    Persist completed driving traces as Parquet.

    One Parquet file is stored for each completed lap.

    Layout:

        output_directory/
            session_id=<session>/
                lap_number=<lap>/
                    trace.parquet

    The dataset is analysis-ready and intentionally keeps
    dense telemetry outside PostgreSQL.
    """

    SCHEMA_VERSION = 1

    DATASET_NAME = (
        "assetto_corsa_lap_trace"
    )

    REQUIRED_COLUMNS: ClassVar[
        frozenset[str]
    ] = frozenset(
        {
            "session_id",
            "lap_number",
            "car_id",
            "track_id",
            "lap_time_ms",
            "sample_index",
            "progress",
            "elapsed_seconds",
            "speed_kmh",
            "throttle",
            "brake",
            "steering_angle_deg",
        }
    )

    def __init__(
        self,
        output_directory: str | Path = (
            "data/silver/lap_traces"
        ),
    ) -> None:
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _validate_partition_value(
        value: str,
        *,
        name: str,
    ) -> None:
        if not value:
            raise ValueError(
                f"{name} cannot be empty"
            )

        if (
            "/" in value
            or "\\" in value
        ):
            raise ValueError(
                f"{name} cannot contain "
                "path separators"
            )

    def path_for(
        self,
        *,
        session_id: str,
        lap_number: int,
    ) -> Path:
        self._validate_partition_value(
            session_id,
            name="session_id",
        )

        if lap_number <= 0:
            raise ValueError(
                "lap_number must be greater than 0"
            )

        return (
            self.output_directory
            / f"session_id={session_id}"
            / (
                "lap_number="
                f"{lap_number:04d}"
            )
            / "trace.parquet"
        )

    @staticmethod
    def _validate_trace(
        trace: LapTrace,
    ) -> None:
        if trace.lap_number <= 0:
            raise ValueError(
                "LapTrace lap_number must "
                "be greater than 0"
            )

        if trace.lap_time_ms <= 0:
            raise ValueError(
                "LapTrace lap_time_ms must "
                "be greater than 0"
            )

        if not trace.samples:
            raise ValueError(
                "Cannot persist an empty LapTrace"
            )

    @staticmethod
    def _rows(
        trace: LapTrace,
    ) -> list[dict]:
        return [
            {
                "session_id": (
                    trace.session_id
                ),
                "lap_number": (
                    trace.lap_number
                ),
                "car_id": (
                    trace.car_id
                ),
                "track_id": (
                    trace.track_id
                ),
                "lap_time_ms": (
                    trace.lap_time_ms
                ),
                "sample_index": (
                    sample_index
                ),
                "progress": (
                    sample.progress
                ),
                "elapsed_seconds": (
                    sample.elapsed_seconds
                ),
                "speed_kmh": (
                    sample.speed_kmh
                ),
                "throttle": (
                    sample.throttle
                ),
                "gear": sample.gear,
                "clutch": sample.clutch,
                "brake": (
                    sample.brake
                ),
                "steering_angle_deg": (
                    sample.steering_angle_deg
                ),
            }
            for (
                sample_index,
                sample,
            ) in enumerate(
                trace.samples
            )
        ]

    def write(
        self,
        trace: LapTrace,
    ) -> Path:
        self._validate_trace(
            trace
        )

        output_file = self.path_for(
            session_id=trace.session_id,
            lap_number=trace.lap_number,
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        table = pa.Table.from_pylist(
            self._rows(
                trace
            )
        )

        metadata = dict(
            table.schema.metadata
            or {}
        )

        metadata.update(
            {
                (
                    b"ac_race_engineer.dataset"
                ): (
                    self.DATASET_NAME.encode(
                        "utf-8"
                    )
                ),
                (
                    b"ac_race_engineer.schema_version"
                ): (
                    str(
                        self.SCHEMA_VERSION
                    ).encode(
                        "utf-8"
                    )
                ),
            }
        )

        table = (
            table.replace_schema_metadata(
                metadata
            )
        )

        temporary_file = (
            output_file.with_name(
                "trace.tmp.parquet"
            )
        )

        try:
            pq.write_table(
                table,
                temporary_file,
                compression="snappy",
            )

            temporary_file.replace(
                output_file
            )

        finally:
            if temporary_file.exists():
                temporary_file.unlink()

        return output_file

    def read(
        self,
        *,
        session_id: str,
        lap_number: int,
    ) -> LapTrace:
        input_file = self.path_for(
            session_id=session_id,
            lap_number=lap_number,
        )

        trace = self.read_file(input_file)
        if trace.session_id != session_id or trace.lap_number != lap_number:
            raise ValueError("LapTrace Parquet does not match the requested session and lap")
        return trace

    @classmethod
    def read_file(cls, input_file: Path) -> LapTrace:
        """Read a cataloged file, including files in a custom capture directory."""

        if not input_file.exists():
            raise FileNotFoundError(
                input_file
            )

        parquet_file = pq.ParquetFile(
            input_file
        )

        table = parquet_file.read()

        missing_columns = (
            cls.REQUIRED_COLUMNS
            - set(
                table.column_names
            )
        )

        if missing_columns:
            missing = ", ".join(
                sorted(
                    missing_columns
                )
            )

            raise ValueError(
                "LapTrace Parquet is missing "
                f"required columns: {missing}"
            )

        rows = table.to_pylist()

        if not rows:
            raise ValueError(
                "LapTrace Parquet contains "
                "no samples"
            )

        first = rows[0]

        expected_session_id = (
            first["session_id"]
        )

        expected_lap_number = int(
            first["lap_number"]
        )

        expected_car_id = (
            first["car_id"]
        )

        expected_track_id = (
            first["track_id"]
        )

        expected_lap_time_ms = int(
            first["lap_time_ms"]
        )

        for row in rows:
            if (
                row["session_id"]
                != expected_session_id
            ):
                raise ValueError(
                    "LapTrace Parquet contains "
                    "multiple session IDs"
                )

            if (
                int(
                    row["lap_number"]
                )
                != expected_lap_number
            ):
                raise ValueError(
                    "LapTrace Parquet contains "
                    "multiple lap numbers"
                )

            if (
                row["car_id"]
                != expected_car_id
            ):
                raise ValueError(
                    "LapTrace Parquet contains "
                    "multiple cars"
                )

            if (
                row["track_id"]
                != expected_track_id
            ):
                raise ValueError(
                    "LapTrace Parquet contains "
                    "multiple tracks"
                )

            if (
                int(
                    row["lap_time_ms"]
                )
                != expected_lap_time_ms
            ):
                raise ValueError(
                    "LapTrace Parquet contains "
                    "multiple lap times"
                )

        ordered_rows = sorted(
            rows,
            key=lambda row: int(
                row["sample_index"]
            ),
        )

        samples = tuple(
            DrivingTraceSample(
                gear=row.get("gear"),
                clutch=row.get("clutch"),
                progress=float(
                    row["progress"]
                ),
                elapsed_seconds=float(
                    row["elapsed_seconds"]
                ),
                speed_kmh=float(
                    row["speed_kmh"]
                ),
                throttle=float(
                    row["throttle"]
                ),
                brake=float(
                    row["brake"]
                ),
                steering_angle_deg=float(
                    row[
                        "steering_angle_deg"
                    ]
                ),
            )
            for row in ordered_rows
        )

        return LapTrace(
            session_id=(
                expected_session_id
            ),
            lap_number=(
                expected_lap_number
            ),
            car_id=(
                expected_car_id
            ),
            track_id=(
                expected_track_id
            ),
            lap_time_ms=(
                expected_lap_time_ms
            ),
            samples=samples,
        )
