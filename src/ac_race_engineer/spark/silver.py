import hashlib
import shutil
from functools import reduce
from pathlib import Path
from typing import ClassVar

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, FloatType

from ac_race_engineer.domain.lakehouse import (
    SparkSilverProcessingResult,
)


class SparkSilverTelemetryProcessor:

    SCHEMA_VERSION = 1

    REQUIRED_COLUMNS: ClassVar[frozenset[str]] = frozenset(
        {
            "timestamp",
            "session_id",
            "sample_index",
            "elapsed_seconds",
            "car_id",
            "track_id",
            "vehicle_speed_kmh",
            "vehicle_rpm",
            "vehicle_throttle",
            "vehicle_brake",
            "vehicle_clutch",
            "vehicle_fuel_l",
            "environment_grip_level",
            "fl_pressure_psi",
            "fr_pressure_psi",
            "rl_pressure_psi",
            "rr_pressure_psi",
            "fl_tyre_temp_core_c",
            "fr_tyre_temp_core_c",
            "rl_tyre_temp_core_c",
            "rr_tyre_temp_core_c",
            "fl_brake_temp_c",
            "fr_brake_temp_c",
            "rl_brake_temp_c",
            "rr_brake_temp_c",
            "fl_load_n",
            "fr_load_n",
            "rl_load_n",
            "rr_load_n",
            "fl_slip_angle_deg",
            "fr_slip_angle_deg",
            "rl_slip_angle_deg",
            "rr_slip_angle_deg",
            "fl_suspension_travel_mm",
            "fr_suspension_travel_mm",
            "rl_suspension_travel_mm",
            "rr_suspension_travel_mm",
        }
    )

    def __init__(
        self,
        spark: SparkSession,
        output_directory: str | Path = "data/silver_spark",
    ):
        self.spark = spark
        self.output_directory = Path(output_directory)

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def process(
        self,
        bronze_file: str | Path,
    ) -> SparkSilverProcessingResult:

        bronze_file = Path(bronze_file)

        if not bronze_file.exists():
            raise FileNotFoundError(
                f"Bronze telemetry file not found: "
                f"{bronze_file}"
            )

        source_checksum = self._calculate_checksum(
            bronze_file
        )

        dataframe = (
            self.spark.read.parquet(
                str(bronze_file)
            )
        )

        self._validate_columns(
            dataframe
        )

        dataframe = dataframe.withColumn(
            "timestamp",
            F.to_timestamp(
                "timestamp"
            ),
        )

        input_rows = dataframe.count()

        if input_rows == 0:
            raise ValueError(
                "Bronze telemetry dataset is empty"
            )

        metadata = (
            dataframe
            .select(
                "session_id",
                "car_id",
                "track_id",
            )
            .distinct()
            .collect()
        )

        if len(metadata) != 1:
            raise ValueError(
                "Expected exactly one session "
                "per Spark Silver dataset"
            )

        metadata_row = metadata[0]

        session_id = str(
            metadata_row["session_id"]
        )
        car_id = str(
            metadata_row["car_id"]
        )
        track_id = str(
            metadata_row["track_id"]
        )

        minimum_timestamp = (
            dataframe
            .agg(
                F.min(
                    "timestamp"
                ).alias(
                    "minimum_timestamp"
                )
            )
            .first()[
                "minimum_timestamp"
            ]
        )

        if minimum_timestamp is None:
            raise ValueError(
                "Dataset has no valid timestamps"
            )

        partition_date = (
            minimum_timestamp
            .date()
            .isoformat()
        )

        session_directory = (
            self.output_directory
            / "telemetry"
            / f"date={partition_date}"
            / f"car_id={car_id}"
            / f"track_id={track_id}"
            / f"session_id={session_id}"
        )

        output_path = (
            session_directory
            / "telemetry"
        )

        manifest_file = (
            session_directory
            / "_manifest.json"
        )

        quarantine_path = (
            self.output_directory
            / "quarantine"
            / f"date={partition_date}"
            / f"car_id={car_id}"
            / f"track_id={track_id}"
            / f"session_id={session_id}"
            / "telemetry"
        )

        existing = self._load_existing_result(
            manifest_file=manifest_file,
            output_path=output_path,
            source_checksum=source_checksum,
        )

        if existing is not None:
            return existing

        deduplicated = (
            dataframe
            .dropDuplicates(
                [
                    "session_id",
                    "sample_index",
                ]
            )
        )

        deduplicated_rows = (
            deduplicated.count()
        )

        duplicate_rows_removed = (
            input_rows
            - deduplicated_rows
        )

        processed = self.transform(deduplicated)

        valid = processed.filter(
            F.col(
                "is_valid"
            )
        )

        invalid = processed.filter(
            ~F.col(
                "is_valid"
            )
        )

        output_rows = valid.count()
        quarantined_rows = invalid.count()

        (
            valid
            .orderBy(
                "timestamp",
                "sample_index",
            )
            .write
            .mode(
                "overwrite"
            )
            .parquet(
                str(output_path)
            )
        )

        quarantine_value = None

        if quarantined_rows > 0:
            (
                invalid
                .orderBy(
                    "timestamp",
                    "sample_index",
                )
                .write
                .mode(
                    "overwrite"
                )
                .parquet(
                    str(quarantine_path)
                )
            )

            quarantine_value = str(
                quarantine_path
            )

        elif quarantine_path.exists():
            shutil.rmtree(
                quarantine_path
            )

        result = SparkSilverProcessingResult(
            session_id=session_id,
            input_rows=input_rows,
            output_rows=output_rows,
            duplicate_rows_removed=(
                duplicate_rows_removed
            ),
            quarantined_rows=(
                quarantined_rows
            ),
            output_path=str(
                output_path
            ),
            quarantine_path=(
                quarantine_value
            ),
            manifest_file=str(
                manifest_file
            ),
            source_checksum=(
                source_checksum
            ),
            status="written",
            partition_date=(
                partition_date
            ),
            car_id=car_id,
            track_id=track_id,
            spark_version=(
                self.spark.version
            ),
        )

        manifest_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        manifest_file.write_text(
            result.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return result

    @classmethod
    def transform(cls, dataframe: DataFrame) -> DataFrame:
        """Shared stateless enrichment for batch and streaming Bronze DataFrames."""
        cls._validate_columns(dataframe)
        dataframe = dataframe.withColumn("timestamp", F.to_timestamp("timestamp"))
        return (
            cls._add_quality_flags(cls._add_features(dataframe))
            .withColumn("silver_processed_at", F.current_timestamp())
            .withColumn("silver_schema_version", F.lit(cls.SCHEMA_VERSION))
        )

    @classmethod
    def _validate_columns(
        cls,
        dataframe: DataFrame,
    ) -> None:

        missing = (
            cls.REQUIRED_COLUMNS
            - set(
                dataframe.columns
            )
        )

        if missing:
            raise ValueError(
                "Missing Bronze columns: "
                + ", ".join(
                    sorted(missing)
                )
            )

    @staticmethod
    def _add_features(
        dataframe: DataFrame,
    ) -> DataFrame:

        dataframe = (
            dataframe
            .withColumn(
                "vehicle_speed_mps",
                F.col(
                    "vehicle_speed_kmh"
                )
                / F.lit(
                    3.6
                ),
            )
            .withColumn(
                "front_pressure_psi",
                (
                    F.col(
                        "fl_pressure_psi"
                    )
                    + F.col(
                        "fr_pressure_psi"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
            .withColumn(
                "rear_pressure_psi",
                (
                    F.col(
                        "rl_pressure_psi"
                    )
                    + F.col(
                        "rr_pressure_psi"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
        )

        dataframe = dataframe.withColumn(
            "front_rear_pressure_delta_psi",
            F.col(
                "front_pressure_psi"
            )
            - F.col(
                "rear_pressure_psi"
            ),
        )

        dataframe = (
            dataframe
            .withColumn(
                "front_core_temp_c",
                (
                    F.col(
                        "fl_tyre_temp_core_c"
                    )
                    + F.col(
                        "fr_tyre_temp_core_c"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
            .withColumn(
                "rear_core_temp_c",
                (
                    F.col(
                        "rl_tyre_temp_core_c"
                    )
                    + F.col(
                        "rr_tyre_temp_core_c"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
        )

        dataframe = dataframe.withColumn(
            "front_rear_core_temp_delta_c",
            F.col(
                "front_core_temp_c"
            )
            - F.col(
                "rear_core_temp_c"
            ),
        )

        dataframe = (
            dataframe
            .withColumn(
                "front_brake_temp_c",
                (
                    F.col(
                        "fl_brake_temp_c"
                    )
                    + F.col(
                        "fr_brake_temp_c"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
            .withColumn(
                "rear_brake_temp_c",
                (
                    F.col(
                        "rl_brake_temp_c"
                    )
                    + F.col(
                        "rr_brake_temp_c"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
        )

        dataframe = dataframe.withColumn(
            "front_rear_brake_temp_delta_c",
            F.col(
                "front_brake_temp_c"
            )
            - F.col(
                "rear_brake_temp_c"
            ),
        )

        dataframe = (
            dataframe
            .withColumn(
                "front_suspension_travel_mm",
                (
                    F.col(
                        "fl_suspension_travel_mm"
                    )
                    + F.col(
                        "fr_suspension_travel_mm"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
            .withColumn(
                "rear_suspension_travel_mm",
                (
                    F.col(
                        "rl_suspension_travel_mm"
                    )
                    + F.col(
                        "rr_suspension_travel_mm"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
        )

        dataframe = dataframe.withColumn(
            "front_rear_suspension_delta_mm",
            F.col(
                "front_suspension_travel_mm"
            )
            - F.col(
                "rear_suspension_travel_mm"
            ),
        )

        dataframe = (
            dataframe
            .withColumn(
                "front_slip_angle_deg",
                (
                    F.abs(
                        F.col(
                            "fl_slip_angle_deg"
                        )
                    )
                    + F.abs(
                        F.col(
                            "fr_slip_angle_deg"
                        )
                    )
                )
                / F.lit(
                    2.0
                ),
            )
            .withColumn(
                "rear_slip_angle_deg",
                (
                    F.abs(
                        F.col(
                            "rl_slip_angle_deg"
                        )
                    )
                    + F.abs(
                        F.col(
                            "rr_slip_angle_deg"
                        )
                    )
                )
                / F.lit(
                    2.0
                ),
            )
        )

        dataframe = dataframe.withColumn(
            "front_rear_slip_delta_deg",
            F.col(
                "front_slip_angle_deg"
            )
            - F.col(
                "rear_slip_angle_deg"
            ),
        )

        dataframe = (
            dataframe
            .withColumn(
                "left_load_n",
                (
                    F.col(
                        "fl_load_n"
                    )
                    + F.col(
                        "rl_load_n"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
            .withColumn(
                "right_load_n",
                (
                    F.col(
                        "fr_load_n"
                    )
                    + F.col(
                        "rr_load_n"
                    )
                )
                / F.lit(
                    2.0
                ),
            )
        )

        return dataframe.withColumn(
            "left_right_load_delta_n",
            F.col(
                "left_load_n"
            )
            - F.col(
                "right_load_n"
            ),
        )

    @classmethod
    def _add_quality_flags(
        cls,
        dataframe: DataFrame,
    ) -> DataFrame:

        missing_conditions = [
            (F.col(column).isNull() | F.isnan(column))
            if isinstance(dataframe.schema[column].dataType, (DoubleType, FloatType))
            else F.col(column).isNull()
            for column in cls.REQUIRED_COLUMNS
        ]

        missing_required = reduce(
            lambda left, right: (
                left | right
            ),
            missing_conditions,
        )

        invalid_controls = (
            (~F.col("vehicle_throttle").between(0.0, 1.0))
            | (~F.col("vehicle_brake").between(0.0, 1.0))
            | (~F.col("vehicle_clutch").between(0.0, 1.0))
        )

        invalid_grip = (
            ~F.col(
                "environment_grip_level"
            ).between(
                0.0,
                1.0,
            )
        )

        positive_pressure_columns = [
            "fl_pressure_psi",
            "fr_pressure_psi",
            "rl_pressure_psi",
            "rr_pressure_psi",
        ]

        non_negative_columns = [
            "vehicle_speed_kmh",
            "vehicle_rpm",
            "vehicle_fuel_l",
            "sample_index",
            "elapsed_seconds",
            "fl_load_n",
            "fr_load_n",
            "rl_load_n",
            "rr_load_n",
            "fl_suspension_travel_mm",
            "fr_suspension_travel_mm",
            "rl_suspension_travel_mm",
            "rr_suspension_travel_mm",
        ]

        invalid_pressure = cls._combine_or(
            [
                F.col(column) <= 0
                for column
                in positive_pressure_columns
            ]
        )

        invalid_non_negative = cls._combine_or(
            [
                F.col(column) < 0
                for column
                in non_negative_columns
            ]
        )

        invalid_physical = (
            invalid_pressure
            | invalid_non_negative
        )

        dataframe = (
            dataframe
            .withColumn(
                "quality_missing_required",
                missing_required,
            )
            .withColumn(
                "quality_invalid_controls",
                F.coalesce(invalid_controls, F.lit(True)),
            )
            .withColumn(
                "quality_invalid_grip",
                F.coalesce(invalid_grip, F.lit(True)),
            )
            .withColumn(
                "quality_invalid_physical",
                F.coalesce(invalid_physical, F.lit(False)),
            )
        )

        dataframe = dataframe.withColumn(
            "quality_issue_count",
            (
                F.col(
                    "quality_missing_required"
                ).cast(
                    "int"
                )
                + F.col(
                    "quality_invalid_controls"
                ).cast(
                    "int"
                )
                + F.col(
                    "quality_invalid_grip"
                ).cast(
                    "int"
                )
                + F.col(
                    "quality_invalid_physical"
                ).cast(
                    "int"
                )
            ),
        )

        return dataframe.withColumn(
            "is_valid",
            F.col(
                "quality_issue_count"
            )
            == F.lit(
                0
            ),
        )

    @staticmethod
    def _combine_or(
        expressions: list[Column],
    ) -> Column:

        return reduce(
            lambda left, right: (
                left | right
            ),
            expressions,
        )

    @staticmethod
    def _calculate_checksum(
        file_path: Path,
    ) -> str:

        digest = hashlib.sha256()

        with file_path.open(
            "rb"
        ) as file:
            while chunk := file.read(
                1024 * 1024
            ):
                digest.update(
                    chunk
                )

        return digest.hexdigest()

    @staticmethod
    def _load_existing_result(
        manifest_file: Path,
        output_path: Path,
        source_checksum: str,
    ) -> SparkSilverProcessingResult | None:

        if (
            not manifest_file.exists()
            or not output_path.exists()
        ):
            return None

        previous = (
            SparkSilverProcessingResult
            .model_validate_json(
                manifest_file.read_text(
                    encoding="utf-8"
                )
            )
        )

        if (
            previous.source_checksum
            != source_checksum
        ):
            return None

        return previous.model_copy(
            update={
                "status": "skipped",
            }
        )