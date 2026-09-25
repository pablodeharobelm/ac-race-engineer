import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import pandas as pd

from ac_race_engineer.domain.lakehouse import (
    GoldAggregationResult,
)


class GoldSessionAggregator:

    SCHEMA_VERSION = 1

    REQUIRED_COLUMNS: ClassVar[set[str]] = {
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

    def __init__(
        self,
        output_directory: str | Path = (
            "data/gold/session_summary"
        ),
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def aggregate(
        self,
        silver_file: str | Path,
    ) -> GoldAggregationResult:

        silver_file = Path(
            silver_file
        )

        if not silver_file.exists():
            raise FileNotFoundError(
                f"Silver telemetry file not found: "
                f"{silver_file}"
            )

        source_checksum = (
            self._calculate_checksum(
                silver_file
            )
        )

        dataframe = pd.read_parquet(
            silver_file
        )

        if dataframe.empty:
            raise ValueError(
                "Silver telemetry dataset is empty"
            )

        self._validate_columns(
            dataframe
        )

        dataframe[
            "timestamp"
        ] = pd.to_datetime(
            dataframe["timestamp"],
            utc=True,
        )

        session_id = self._single_value(
            dataframe,
            "session_id",
        )

        car_id = self._single_value(
            dataframe,
            "car_id",
        )

        track_id = self._single_value(
            dataframe,
            "track_id",
        )

        partition_date = (
            dataframe[
                "timestamp"
            ]
            .min()
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

        output_file = (
            session_directory
            / "summary.parquet"
        )

        manifest_file = (
            session_directory
            / "_manifest.json"
        )

        existing_result = (
            self._load_existing_result(
                manifest_file=manifest_file,
                output_file=output_file,
                source_checksum=(
                    source_checksum
                ),
            )
        )

        if existing_result is not None:
            return existing_result

        summary = self._build_summary(
            dataframe
        )

        session_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        summary_dataframe = pd.DataFrame(
            [summary]
        )

        summary_dataframe.to_parquet(
            output_file,
            index=False,
        )

        result = GoldAggregationResult(
            session_id=session_id,
            source_rows=len(
                dataframe
            ),
            output_rows=1,
            output_file=str(
                output_file
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
        dataframe: pd.DataFrame,
    ) -> None:

        missing_columns = (
            self.REQUIRED_COLUMNS
            - set(dataframe.columns)
        )

        if missing_columns:

            missing = ", ".join(
                sorted(
                    missing_columns
                )
            )

            raise ValueError(
                "Missing Silver columns: "
                f"{missing}"
            )

    @staticmethod
    def _single_value(
        dataframe: pd.DataFrame,
        column: str,
    ) -> str:

        values = (
            dataframe[
                column
            ]
            .dropna()
            .unique()
        )

        if len(values) != 1:
            raise ValueError(
                f"Expected exactly one "
                f"{column} per Gold dataset"
            )

        return str(
            values[0]
        )

    @staticmethod
    def _optional_single_value(
        dataframe: pd.DataFrame,
        column: str,
    ) -> str | None:

        values = (
            dataframe[
                column
            ]
            .dropna()
            .unique()
        )

        if len(values) == 0:
            return None

        if len(values) != 1:
            raise ValueError(
                f"Expected at most one "
                f"{column} per Gold dataset"
            )

        return str(
            values[0]
        )

    def _build_summary(
        self,
        dataframe: pd.DataFrame,
    ) -> dict:

        dataframe = (
            dataframe
            .sort_values(
                [
                    "timestamp",
                    "sample_index",
                ]
            )
            .reset_index(
                drop=True
            )
        )

        first_row = (
            dataframe.iloc[0]
        )

        last_row = (
            dataframe.iloc[-1]
        )

        fuel_used_l = max(
            0.0,
            float(
                first_row[
                    "vehicle_fuel_l"
                ]
                - last_row[
                    "vehicle_fuel_l"
                ]
            ),
        )

        maximum_braking_g = max(
            0.0,
            float(
                -dataframe[
                    "vehicle_longitudinal_g"
                ].min()
            ),
        )

        return {
            "session_id": (
                self._single_value(
                    dataframe,
                    "session_id",
                )
            ),
            "car_id": (
                self._single_value(
                    dataframe,
                    "car_id",
                )
            ),
            "track_id": (
                self._single_value(
                    dataframe,
                    "track_id",
                )
            ),
            "setup_id": (
                self._optional_single_value(
                    dataframe,
                    "setup_id",
                )
            ),
            "session_type": (
                self._single_value(
                    dataframe,
                    "session_type",
                )
            ),
            "telemetry_source": (
                self._single_value(
                    dataframe,
                    "telemetry_source",
                )
            ),
            "started_at": (
                dataframe[
                    "timestamp"
                ].min()
            ),
            "ended_at": (
                dataframe[
                    "timestamp"
                ].max()
            ),
            "duration_seconds": float(
                dataframe[
                    "elapsed_seconds"
                ].max()
                - dataframe[
                    "elapsed_seconds"
                ].min()
            ),
            "sample_count": len(
                dataframe
            ),
            "maximum_speed_kmh": float(
                dataframe[
                    "vehicle_speed_kmh"
                ].max()
            ),
            "average_speed_kmh": float(
                dataframe[
                    "vehicle_speed_kmh"
                ].mean()
            ),
            "average_rpm": float(
                dataframe[
                    "vehicle_rpm"
                ].mean()
            ),
            "average_throttle": float(
                dataframe[
                    "vehicle_throttle"
                ].mean()
            ),
            "average_brake": float(
                dataframe[
                    "vehicle_brake"
                ].mean()
            ),
            "maximum_lateral_g": float(
                dataframe[
                    "vehicle_lateral_g"
                ].abs().max()
            ),
            "maximum_braking_g": (
                maximum_braking_g
            ),
            "fuel_used_l": fuel_used_l,
            "average_front_pressure_psi": float(
                dataframe[
                    "front_pressure_psi"
                ].mean()
            ),
            "average_rear_pressure_psi": float(
                dataframe[
                    "rear_pressure_psi"
                ].mean()
            ),
            "average_front_core_temp_c": float(
                dataframe[
                    "front_core_temp_c"
                ].mean()
            ),
            "average_rear_core_temp_c": float(
                dataframe[
                    "rear_core_temp_c"
                ].mean()
            ),
            "peak_front_core_temp_c": float(
                dataframe[
                    "front_core_temp_c"
                ].max()
            ),
            "peak_rear_core_temp_c": float(
                dataframe[
                    "rear_core_temp_c"
                ].max()
            ),
            "average_front_brake_temp_c": float(
                dataframe[
                    "front_brake_temp_c"
                ].mean()
            ),
            "average_rear_brake_temp_c": float(
                dataframe[
                    "rear_brake_temp_c"
                ].mean()
            ),
            "peak_front_brake_temp_c": float(
                dataframe[
                    "front_brake_temp_c"
                ].max()
            ),
            "peak_rear_brake_temp_c": float(
                dataframe[
                    "rear_brake_temp_c"
                ].max()
            ),
            "average_front_suspension_travel_mm": float(
                dataframe[
                    "front_suspension_travel_mm"
                ].mean()
            ),
            "average_rear_suspension_travel_mm": float(
                dataframe[
                    "rear_suspension_travel_mm"
                ].mean()
            ),
            "maximum_front_suspension_travel_mm": float(
                dataframe[
                    "front_suspension_travel_mm"
                ].max()
            ),
            "maximum_rear_suspension_travel_mm": float(
                dataframe[
                    "rear_suspension_travel_mm"
                ].max()
            ),
            "average_front_slip_angle_deg": float(
                dataframe[
                    "front_slip_angle_deg"
                ].mean()
            ),
            "average_rear_slip_angle_deg": float(
                dataframe[
                    "rear_slip_angle_deg"
                ].mean()
            ),
            "average_front_rear_slip_delta_deg": float(
                dataframe[
                    "front_rear_slip_delta_deg"
                ].mean()
            ),
            "average_left_right_load_delta_n": float(
                dataframe[
                    "left_right_load_delta_n"
                ].mean()
            ),
            "valid_row_percentage": float(
                dataframe[
                    "is_valid"
                ].mean()
                * 100
            ),
            "gold_processed_at": (
                datetime.now(UTC)
            ),
            "gold_schema_version": (
                self.SCHEMA_VERSION
            ),
        }

    @staticmethod
    def _calculate_checksum(
        file_path: Path,
    ) -> str:

        digest = hashlib.sha256()

        with file_path.open(
            "rb"
        ) as file:

            for chunk in iter(
                lambda: file.read(
                    1024 * 1024
                ),
                b"",
            ):
                digest.update(
                    chunk
                )

        return digest.hexdigest()

    @staticmethod
    def _load_existing_result(
        manifest_file: Path,
        output_file: Path,
        source_checksum: str,
    ) -> GoldAggregationResult | None:

        if (
            not manifest_file.exists()
            or not output_file.exists()
        ):
            return None

        result = (
            GoldAggregationResult
            .model_validate_json(
                manifest_file.read_text(
                    encoding="utf-8"
                )
            )
        )

        if (
            result.source_checksum
            != source_checksum
        ):
            return None

        return result.model_copy(
            update={
                "status": "skipped"
            }
        )

