import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

import pandas as pd

from ac_race_engineer.domain.lakehouse import (
    SilverProcessingResult,
)


class SilverTelemetryProcessor:

    SCHEMA_VERSION = 1

    REQUIRED_COLUMNS: ClassVar[set[str]] = {
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

    def __init__(
        self,
        output_directory: str | Path = "data/silver",
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def process(
        self,
        bronze_file: str | Path,
    ) -> SilverProcessingResult:

        bronze_file = Path(
            bronze_file
        )

        if not bronze_file.exists():
            raise FileNotFoundError(
                f"Bronze telemetry file not found: "
                f"{bronze_file}"
            )

        source_checksum = (
            self._calculate_checksum(
                bronze_file
            )
        )

        dataframe = pd.read_parquet(
            bronze_file
        )

        if dataframe.empty:
            raise ValueError(
                "Bronze telemetry dataset is empty"
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

        session_id = (
            self._single_value(
                dataframe,
                "session_id",
            )
        )

        car_id = (
            self._single_value(
                dataframe,
                "car_id",
            )
        )

        track_id = (
            self._single_value(
                dataframe,
                "track_id",
            )
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
            / "telemetry"
            / f"date={partition_date}"
            / f"car_id={car_id}"
            / f"track_id={track_id}"
            / f"session_id={session_id}"
        )

        output_file = (
            session_directory
            / "telemetry.parquet"
        )

        manifest_file = (
            session_directory
            / "_manifest.json"
        )

        quarantine_file = (
            self.output_directory
            / "quarantine"
            / f"date={partition_date}"
            / f"car_id={car_id}"
            / f"track_id={track_id}"
            / f"session_id={session_id}"
            / "telemetry.parquet"
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

        input_rows = len(
            dataframe
        )

        duplicate_mask = (
            dataframe.duplicated(
                subset=[
                    "session_id",
                    "sample_index",
                ],
                keep="first",
            )
        )

        duplicate_rows_removed = int(
            duplicate_mask.sum()
        )

        dataframe = (
            dataframe.loc[
                ~duplicate_mask
            ]
            .copy()
        )

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

        dataframe = self._add_features(
            dataframe
        )

        dataframe = self._add_quality_flags(
            dataframe
        )

        valid_data = (
            dataframe.loc[
                dataframe["is_valid"]
            ]
            .copy()
        )

        invalid_data = (
            dataframe.loc[
                ~dataframe["is_valid"]
            ]
            .copy()
        )

        processed_at = (
            datetime.now(UTC)
        )

        for target in (
            valid_data,
            invalid_data,
        ):
            target[
                "silver_processed_at"
            ] = processed_at

            target[
                "silver_schema_version"
            ] = self.SCHEMA_VERSION

        session_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        valid_data.to_parquet(
            output_file,
            index=False,
        )

        quarantine_path = None

        if not invalid_data.empty:

            quarantine_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            invalid_data.to_parquet(
                quarantine_file,
                index=False,
            )

            quarantine_path = str(
                quarantine_file
            )

        elif quarantine_file.exists():

            quarantine_file.unlink()

        result = SilverProcessingResult(
            session_id=session_id,
            input_rows=input_rows,
            output_rows=len(
                valid_data
            ),
            duplicate_rows_removed=(
                duplicate_rows_removed
            ),
            quarantined_rows=len(
                invalid_data
            ),
            output_file=str(
                output_file
            ),
            quarantine_file=(
                quarantine_path
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
                f"Missing Bronze columns: "
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
                f"{column} per Silver dataset"
            )

        return str(
            values[0]
        )

    @staticmethod
    def _add_features(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        dataframe = (
            dataframe.copy()
        )

        dataframe[
            "vehicle_speed_mps"
        ] = (
            dataframe[
                "vehicle_speed_kmh"
            ]
            / 3.6
        )

        dataframe[
            "front_pressure_psi"
        ] = (
            dataframe[
                [
                    "fl_pressure_psi",
                    "fr_pressure_psi",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "rear_pressure_psi"
        ] = (
            dataframe[
                [
                    "rl_pressure_psi",
                    "rr_pressure_psi",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "front_rear_pressure_delta_psi"
        ] = (
            dataframe[
                "front_pressure_psi"
            ]
            - dataframe[
                "rear_pressure_psi"
            ]
        )

        dataframe[
            "front_core_temp_c"
        ] = (
            dataframe[
                [
                    "fl_tyre_temp_core_c",
                    "fr_tyre_temp_core_c",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "rear_core_temp_c"
        ] = (
            dataframe[
                [
                    "rl_tyre_temp_core_c",
                    "rr_tyre_temp_core_c",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "front_rear_core_temp_delta_c"
        ] = (
            dataframe[
                "front_core_temp_c"
            ]
            - dataframe[
                "rear_core_temp_c"
            ]
        )

        dataframe[
            "front_brake_temp_c"
        ] = (
            dataframe[
                [
                    "fl_brake_temp_c",
                    "fr_brake_temp_c",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "rear_brake_temp_c"
        ] = (
            dataframe[
                [
                    "rl_brake_temp_c",
                    "rr_brake_temp_c",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "front_rear_brake_temp_delta_c"
        ] = (
            dataframe[
                "front_brake_temp_c"
            ]
            - dataframe[
                "rear_brake_temp_c"
            ]
        )

        dataframe[
            "front_suspension_travel_mm"
        ] = (
            dataframe[
                [
                    "fl_suspension_travel_mm",
                    "fr_suspension_travel_mm",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "rear_suspension_travel_mm"
        ] = (
            dataframe[
                [
                    "rl_suspension_travel_mm",
                    "rr_suspension_travel_mm",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "front_rear_suspension_delta_mm"
        ] = (
            dataframe[
                "front_suspension_travel_mm"
            ]
            - dataframe[
                "rear_suspension_travel_mm"
            ]
        )

        dataframe[
            "front_slip_angle_deg"
        ] = (
            dataframe[
                [
                    "fl_slip_angle_deg",
                    "fr_slip_angle_deg",
                ]
            ]
            .abs()
            .mean(
                axis=1
            )
        )

        dataframe[
            "rear_slip_angle_deg"
        ] = (
            dataframe[
                [
                    "rl_slip_angle_deg",
                    "rr_slip_angle_deg",
                ]
            ]
            .abs()
            .mean(
                axis=1
            )
        )

        dataframe[
            "front_rear_slip_delta_deg"
        ] = (
            dataframe[
                "front_slip_angle_deg"
            ]
            - dataframe[
                "rear_slip_angle_deg"
            ]
        )

        dataframe[
            "left_load_n"
        ] = (
            dataframe[
                [
                    "fl_load_n",
                    "rl_load_n",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "right_load_n"
        ] = (
            dataframe[
                [
                    "fr_load_n",
                    "rr_load_n",
                ]
            ]
            .mean(
                axis=1
            )
        )

        dataframe[
            "left_right_load_delta_n"
        ] = (
            dataframe[
                "left_load_n"
            ]
            - dataframe[
                "right_load_n"
            ]
        )

        return dataframe

    def _add_quality_flags(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        dataframe = (
            dataframe.copy()
        )

        required = sorted(
            self.REQUIRED_COLUMNS
        )

        dataframe[
            "quality_missing_required"
        ] = (
            dataframe[
                required
            ]
            .isna()
            .any(
                axis=1
            )
        )

        dataframe[
            "quality_invalid_controls"
        ] = (
            ~dataframe[
                "vehicle_throttle"
            ].between(
                0.0,
                1.0,
            )
            | ~dataframe[
                "vehicle_brake"
            ].between(
                0.0,
                1.0,
            )
            | ~dataframe[
                "vehicle_clutch"
            ].between(
                0.0,
                1.0,
            )
        )

        dataframe[
            "quality_invalid_grip"
        ] = (
            ~dataframe[
                "environment_grip_level"
            ].between(
                0.0,
                1.0,
            )
        )

        pressure_columns = [
            "fl_pressure_psi",
            "fr_pressure_psi",
            "rl_pressure_psi",
            "rr_pressure_psi",
        ]

        load_columns = [
            "fl_load_n",
            "fr_load_n",
            "rl_load_n",
            "rr_load_n",
        ]

        suspension_columns = [
            "fl_suspension_travel_mm",
            "fr_suspension_travel_mm",
            "rl_suspension_travel_mm",
            "rr_suspension_travel_mm",
        ]

        dataframe[
            "quality_invalid_physical"
        ] = (
            (
                dataframe[
                    "vehicle_speed_kmh"
                ]
                < 0
            )
            | (
                dataframe[
                    "vehicle_rpm"
                ]
                < 0
            )
            | (
                dataframe[
                    "vehicle_fuel_l"
                ]
                < 0
            )
            | (
                dataframe[
                    pressure_columns
                ]
                <= 0
            ).any(
                axis=1
            )
            | (
                dataframe[
                    load_columns
                ]
                < 0
            ).any(
                axis=1
            )
            | (
                dataframe[
                    suspension_columns
                ]
                < 0
            ).any(
                axis=1
            )
            | (
                dataframe[
                    "sample_index"
                ]
                < 0
            )
            | (
                dataframe[
                    "elapsed_seconds"
                ]
                < 0
            )
        )

        quality_columns = [
            "quality_missing_required",
            "quality_invalid_controls",
            "quality_invalid_grip",
            "quality_invalid_physical",
        ]

        dataframe[
            "quality_issue_count"
        ] = (
            dataframe[
                quality_columns
            ]
            .astype(
                "int8"
            )
            .sum(
                axis=1
            )
        )

        dataframe[
            "is_valid"
        ] = (
            dataframe[
                "quality_issue_count"
            ]
            == 0
        )

        return dataframe

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
    ) -> SilverProcessingResult | None:

        if (
            not manifest_file.exists()
            or not output_file.exists()
        ):
            return None

        result = (
            SilverProcessingResult
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