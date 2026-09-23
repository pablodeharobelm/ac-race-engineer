import math
from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession

from ac_race_engineer.domain.lakehouse import (
    SilverParityMetric,
    SilverParityReport,
)
from ac_race_engineer.spark.sql_analytics import (
    SparkSQLSessionAnalyzer,
)


class SilverParityValidator:

    def __init__(
        self,
        spark: SparkSession,
        tolerance: float = 1e-6,
    ):
        self.spark = spark
        self.tolerance = tolerance

    def validate(
        self,
        pandas_silver_file: str | Path,
        spark_silver_path: str | Path,
    ) -> SilverParityReport:

        pandas_silver_file = Path(
            pandas_silver_file
        )

        spark_silver_path = Path(
            spark_silver_path
        )

        if not pandas_silver_file.exists():
            raise FileNotFoundError(
                f"Pandas Silver file not found: "
                f"{pandas_silver_file}"
            )

        if not spark_silver_path.exists():
            raise FileNotFoundError(
                f"Spark Silver dataset not found: "
                f"{spark_silver_path}"
            )

        pandas_df = pd.read_parquet(
            pandas_silver_file
        )

        spark_df = (
            self.spark
            .read
            .parquet(
                str(
                    spark_silver_path
                )
            )
        )

        if pandas_df.empty:
            raise ValueError(
                "Pandas Silver dataset is empty"
            )

        spark_rows = spark_df.count()

        if spark_rows == 0:
            raise ValueError(
                "Spark Silver dataset is empty"
            )

        session_ids = (
            pandas_df[
                "session_id"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        if len(session_ids) != 1:
            raise ValueError(
                "Expected one session in "
                "Pandas Silver dataset"
            )

        session_id = str(
            session_ids[0]
        )

        analyzer = (
            SparkSQLSessionAnalyzer(
                spark=self.spark
            )
        )

        spark_summary = (
            analyzer.analyze(
                spark_silver_path
            )
        )

        if (
            spark_summary.session_id
            != session_id
        ):
            raise ValueError(
                "Pandas and Spark datasets "
                "belong to different sessions"
            )

        pandas_metrics = {
            "duration_seconds": (
                float(
                    pandas_df[
                        "elapsed_seconds"
                    ].max()
                )
                - float(
                    pandas_df[
                        "elapsed_seconds"
                    ].min()
                )
            ),
            "maximum_speed_kmh": float(
                pandas_df[
                    "vehicle_speed_kmh"
                ].max()
            ),
            "average_speed_kmh": float(
                pandas_df[
                    "vehicle_speed_kmh"
                ].mean()
            ),
            "average_front_pressure_psi": float(
                pandas_df[
                    "front_pressure_psi"
                ].mean()
            ),
            "average_rear_pressure_psi": float(
                pandas_df[
                    "rear_pressure_psi"
                ].mean()
            ),
            "average_front_core_temp_c": float(
                pandas_df[
                    "front_core_temp_c"
                ].mean()
            ),
            "average_rear_core_temp_c": float(
                pandas_df[
                    "rear_core_temp_c"
                ].mean()
            ),
            "average_front_brake_temp_c": float(
                pandas_df[
                    "front_brake_temp_c"
                ].mean()
            ),
            "average_rear_brake_temp_c": float(
                pandas_df[
                    "rear_brake_temp_c"
                ].mean()
            ),
            "average_front_slip_angle_deg": float(
                pandas_df[
                    "front_slip_angle_deg"
                ].mean()
            ),
            "average_rear_slip_angle_deg": float(
                pandas_df[
                    "rear_slip_angle_deg"
                ].mean()
            ),
            "valid_row_percentage": float(
                pandas_df[
                    "is_valid"
                ].mean()
                * 100.0
            ),
        }

        spark_metrics = {
            "duration_seconds": (
                spark_summary
                .duration_seconds
            ),
            "maximum_speed_kmh": (
                spark_summary
                .maximum_speed_kmh
            ),
            "average_speed_kmh": (
                spark_summary
                .average_speed_kmh
            ),
            "average_front_pressure_psi": (
                spark_summary
                .average_front_pressure_psi
            ),
            "average_rear_pressure_psi": (
                spark_summary
                .average_rear_pressure_psi
            ),
            "average_front_core_temp_c": (
                spark_summary
                .average_front_core_temp_c
            ),
            "average_rear_core_temp_c": (
                spark_summary
                .average_rear_core_temp_c
            ),
            "average_front_brake_temp_c": (
                spark_summary
                .average_front_brake_temp_c
            ),
            "average_rear_brake_temp_c": (
                spark_summary
                .average_rear_brake_temp_c
            ),
            "average_front_slip_angle_deg": (
                spark_summary
                .average_front_slip_angle_deg
            ),
            "average_rear_slip_angle_deg": (
                spark_summary
                .average_rear_slip_angle_deg
            ),
            "valid_row_percentage": (
                spark_summary
                .valid_row_percentage
            ),
        }

        metrics = []

        for (
            metric_name,
            pandas_value,
        ) in pandas_metrics.items():

            spark_value = (
                spark_metrics[
                    metric_name
                ]
            )

            difference = abs(
                pandas_value
                - spark_value
            )

            match = math.isclose(
                pandas_value,
                spark_value,
                rel_tol=self.tolerance,
                abs_tol=self.tolerance,
            )

            metrics.append(
                SilverParityMetric(
                    metric=metric_name,
                    pandas_value=(
                        pandas_value
                    ),
                    spark_value=(
                        spark_value
                    ),
                    absolute_difference=(
                        difference
                    ),
                    within_tolerance=(
                        match
                    ),
                )
            )

        pandas_indices = sorted(
            pandas_df[
                "sample_index"
            ]
            .astype(
                int
            )
            .tolist()
        )

        spark_indices = sorted(
            int(
                row[
                    "sample_index"
                ]
            )
            for row in (
                spark_df
                .select(
                    "sample_index"
                )
                .collect()
            )
        )

        row_count_match = (
            len(
                pandas_df
            )
            == spark_rows
        )

        sample_index_match = (
            pandas_indices
            == spark_indices
        )

        max_difference = max(
            (
                metric.absolute_difference
                for metric in metrics
            ),
            default=0.0,
        )

        all_metrics_match = all(
            metric.within_tolerance
            for metric in metrics
        )

        parity_passed = (
            row_count_match
            and sample_index_match
            and all_metrics_match
        )

        return SilverParityReport(
            session_id=session_id,
            pandas_rows=len(
                pandas_df
            ),
            spark_rows=(
                spark_rows
            ),
            row_count_match=(
                row_count_match
            ),
            sample_index_match=(
                sample_index_match
            ),
            tolerance=(
                self.tolerance
            ),
            metrics=metrics,
            max_absolute_difference=(
                max_difference
            ),
            all_metrics_match=(
                all_metrics_match
            ),
            parity_passed=(
                parity_passed
            ),
        )