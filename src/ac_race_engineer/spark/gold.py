import hashlib
from pathlib import Path
from typing import ClassVar

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from ac_race_engineer.domain.lakehouse import (
    SparkGoldAggregationResult,
)


class SparkGoldSessionAggregator:

    SCHEMA_VERSION = 1

    REQUIRED_COLUMNS: ClassVar[frozenset[str]] = frozenset(
        {
            "timestamp",
            "session_id",
            "car_id",
            "track_id",
            "setup_id",
            "session_type",
            "telemetry_source",
            "sample_index",
            "elapsed_seconds",
            "vehicle_speed_kmh",
            "vehicle_rpm",
            "vehicle_throttle",
            "vehicle_brake",
            "vehicle_fuel_l",
            "vehicle_lateral_g",
            "vehicle_longitudinal_g",
            "front_pressure_psi",
            "rear_pressure_psi",
            "front_core_temp_c",
            "rear_core_temp_c",
            "front_brake_temp_c",
            "rear_brake_temp_c",
            "front_suspension_travel_mm",
            "rear_suspension_travel_mm",
            "front_slip_angle_deg",
            "rear_slip_angle_deg",
            "front_rear_slip_delta_deg",
            "left_right_load_delta_n",
            "is_valid",
        }
    )

    def __init__(
        self,
        spark: SparkSession,
        output_directory: str | Path = (
            "data/gold_spark/session_summary"
        ),
    ):
        self.spark = spark
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def aggregate(
        self,
        silver_path: str | Path,
    ) -> SparkGoldAggregationResult:

        silver_path = Path(
            silver_path
        )

        if not silver_path.exists():
            raise FileNotFoundError(
                f"Spark Silver dataset not found: "
                f"{silver_path}"
            )

        dataframe = (
            self.spark
            .read
            .parquet(
                str(
                    silver_path
                )
            )
        )

        self._validate_columns(
            dataframe
        )

        source_checksum = self._calculate_checksum(dataframe)

        source_rows = dataframe.count()

        if source_rows == 0:
            raise ValueError(
                "Spark Silver dataset is empty"
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
                "per Spark Gold aggregation"
            )

        metadata_row = metadata[0]

        session_id = str(
            metadata_row[
                "session_id"
            ]
        )

        car_id = str(
            metadata_row[
                "car_id"
            ]
        )

        track_id = str(
            metadata_row[
                "track_id"
            ]
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
                "Spark Silver dataset "
                "contains no timestamps"
            )

        partition_date = (
            minimum_timestamp
            .date()
            .isoformat()
        )

        session_directory = (
            self.output_directory
            / f"date={partition_date}"
            / f"car_id={car_id}"
            / f"track_id={track_id}"
            / f"session_id={session_id}"
        )

        output_path = (
            session_directory
            / "summary"
        )

        manifest_file = (
            session_directory
            / "_manifest.json"
        )

        existing = (
            self._load_existing_result(
                manifest_file=manifest_file,
                output_path=output_path,
                source_checksum=(
                    source_checksum
                ),
            )
        )

        if existing is not None:
            return existing

        summary = self._build_summary(
            dataframe
        )

        output_rows = summary.count()

        if output_rows != 1:
            raise ValueError(
                "Spark Gold must produce "
                "exactly one row per session"
            )

        (
            summary
            .coalesce(
                1
            )
            .write
            .mode(
                "overwrite"
            )
            .parquet(
                str(
                    output_path
                )
            )
        )

        result = (
            SparkGoldAggregationResult(
                session_id=session_id,
                source_rows=source_rows,
                output_rows=output_rows,
                output_path=str(
                    output_path
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

    def _validate_columns(
        self,
        dataframe: DataFrame,
    ) -> None:

        missing = (
            self.REQUIRED_COLUMNS
            - set(
                dataframe.columns
            )
        )

        if missing:
            raise ValueError(
                "Missing Spark Silver columns: "
                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )

    @classmethod
    def _build_summary(
        cls,
        dataframe: DataFrame,
    ) -> DataFrame:

        summary = dataframe.agg(
            F.first(
                "session_id",
                ignorenulls=True,
            ).alias(
                "session_id"
            ),

            F.first(
                "car_id",
                ignorenulls=True,
            ).alias(
                "car_id"
            ),

            F.first(
                "track_id",
                ignorenulls=True,
            ).alias(
                "track_id"
            ),

            F.first(
                "setup_id",
                ignorenulls=True,
            ).alias(
                "setup_id"
            ),

            F.first(
                "session_type",
                ignorenulls=True,
            ).alias(
                "session_type"
            ),

            F.first(
                "telemetry_source",
                ignorenulls=True,
            ).alias(
                "telemetry_source"
            ),

            F.min(
                "timestamp"
            ).alias(
                "started_at"
            ),

            F.max(
                "timestamp"
            ).alias(
                "ended_at"
            ),

            (
                F.max(
                    "elapsed_seconds"
                )
                - F.min(
                    "elapsed_seconds"
                )
            ).alias(
                "duration_seconds"
            ),

            F.count(
                F.lit(
                    1
                )
            ).alias(
                "sample_count"
            ),

            F.max(
                "vehicle_speed_kmh"
            ).alias(
                "maximum_speed_kmh"
            ),

            F.avg(
                "vehicle_speed_kmh"
            ).alias(
                "average_speed_kmh"
            ),

            F.avg(
                "vehicle_rpm"
            ).alias(
                "average_rpm"
            ),

            F.avg(
                "vehicle_throttle"
            ).alias(
                "average_throttle"
            ),

            F.avg(
                "vehicle_brake"
            ).alias(
                "average_brake"
            ),

            F.max(
                F.abs(
                    F.col(
                        "vehicle_lateral_g"
                    )
                )
            ).alias(
                "maximum_lateral_g"
            ),

            F.greatest(
                F.lit(
                    0.0
                ),
                -F.min(
                    "vehicle_longitudinal_g"
                ),
            ).alias(
                "maximum_braking_g"
            ),

            F.min_by(
                "vehicle_fuel_l",
                F.struct("timestamp", "sample_index"),
            ).alias(
                "initial_fuel_l"
            ),

            F.max_by(
                "vehicle_fuel_l",
                F.struct("timestamp", "sample_index"),
            ).alias(
                "final_fuel_l"
            ),

            F.avg(
                "front_pressure_psi"
            ).alias(
                "average_front_pressure_psi"
            ),

            F.avg(
                "rear_pressure_psi"
            ).alias(
                "average_rear_pressure_psi"
            ),

            F.avg(
                "front_core_temp_c"
            ).alias(
                "average_front_core_temp_c"
            ),

            F.max(
                "front_core_temp_c"
            ).alias(
                "peak_front_core_temp_c"
            ),

            F.avg(
                "rear_core_temp_c"
            ).alias(
                "average_rear_core_temp_c"
            ),

            F.max(
                "rear_core_temp_c"
            ).alias(
                "peak_rear_core_temp_c"
            ),

            F.avg(
                "front_brake_temp_c"
            ).alias(
                "average_front_brake_temp_c"
            ),

            F.max(
                "front_brake_temp_c"
            ).alias(
                "peak_front_brake_temp_c"
            ),

            F.avg(
                "rear_brake_temp_c"
            ).alias(
                "average_rear_brake_temp_c"
            ),

            F.max(
                "rear_brake_temp_c"
            ).alias(
                "peak_rear_brake_temp_c"
            ),

            F.avg(
                "front_suspension_travel_mm"
            ).alias(
                "average_front_suspension_travel_mm"
            ),

            F.max(
                "front_suspension_travel_mm"
            ).alias(
                "maximum_front_suspension_travel_mm"
            ),

            F.avg(
                "rear_suspension_travel_mm"
            ).alias(
                "average_rear_suspension_travel_mm"
            ),

            F.max(
                "rear_suspension_travel_mm"
            ).alias(
                "maximum_rear_suspension_travel_mm"
            ),

            F.avg(
                "front_slip_angle_deg"
            ).alias(
                "average_front_slip_angle_deg"
            ),

            F.avg(
                "rear_slip_angle_deg"
            ).alias(
                "average_rear_slip_angle_deg"
            ),

            F.avg(
                "front_rear_slip_delta_deg"
            ).alias(
                "average_front_rear_slip_delta_deg"
            ),

            F.avg(
                "left_right_load_delta_n"
            ).alias(
                "average_left_right_load_delta_n"
            ),

            (
                F.avg(
                    F.col(
                        "is_valid"
                    ).cast(
                        "double"
                    )
                )
                * F.lit(
                    100.0
                )
            ).alias(
                "valid_row_percentage"
            ),
        )

        summary = summary.withColumn(
            "fuel_used_l",
            F.greatest(
                F.lit(
                    0.0
                ),
                F.col(
                    "initial_fuel_l"
                )
                - F.col(
                    "final_fuel_l"
                ),
            ),
        )

        summary = summary.drop(
            "initial_fuel_l",
            "final_fuel_l",
        )

        return (
            summary
            .withColumn(
                "gold_processed_at",
                F.current_timestamp(),
            )
            .withColumn(
                "gold_schema_version",
                F.lit(
                    cls.SCHEMA_VERSION
                ),
            )
        )

    @staticmethod
    def _calculate_checksum(
        dataframe: DataFrame,
    ) -> str:

        columns = [
            F.col(
                column
            )
            for column in sorted(
                dataframe.columns
            )
        ]

        row_hashes = (
            dataframe
            .select(
                F.xxhash64(
                    F.to_json(
                        F.struct(*columns),
                        options={
                            "ignoreNullFields": "false",
                            "timeZone": "UTC",
                            "timestampFormat": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX",
                            "timestampNTZFormat": "yyyy-MM-dd'T'HH:mm:ss.SSSSSS",
                        },
                    )
                ).alias(
                    "_row_hash"
                )
            )
        )

        fingerprint = (
            row_hashes
            .agg(
                F.count(
                    F.lit(
                        1
                    )
                ).alias(
                    "row_count"
                ),
                F.sum(
                    F.col(
                        "_row_hash"
                    ).cast(
                        "decimal(38,0)"
                    )
                ).alias(
                    "hash_sum"
                ),
                F.min(
                    "_row_hash"
                ).alias(
                    "hash_min"
                ),
                F.max(
                    "_row_hash"
                ).alias(
                    "hash_max"
                ),
            )
            .first()
        )

        if (
            fingerprint is None
            or fingerprint[
                "row_count"
            ]
            == 0
        ):
            raise ValueError(
                "Spark Silver dataset "
                "is empty"
            )

        schema = dataframe.select(*columns).schema.simpleString()
        fingerprint_text = schema + "|" + "|".join(
            [
                str(
                    fingerprint[
                        "row_count"
                    ]
                ),
                str(
                    fingerprint[
                        "hash_sum"
                    ]
                ),
                str(
                    fingerprint[
                        "hash_min"
                    ]
                ),
                str(
                    fingerprint[
                        "hash_max"
                    ]
                ),
            ]
        )

        return hashlib.sha256(
            fingerprint_text.encode(
                "utf-8"
            )
        ).hexdigest()

    @staticmethod
    def _load_existing_result(
        manifest_file: Path,
        output_path: Path,
        source_checksum: str,
    ) -> SparkGoldAggregationResult | None:

        if (
            not manifest_file.exists()
            or not output_path.exists()
        ):
            return None

        previous = (
            SparkGoldAggregationResult
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

