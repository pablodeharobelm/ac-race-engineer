from pathlib import Path

from ac_race_engineer.lakehouse.silver import (
    SilverTelemetryProcessor,
)
from ac_race_engineer.spark.parity import (
    SilverParityValidator,
)
from ac_race_engineer.spark.session import (
    create_spark_session,
)
from ac_race_engineer.spark.silver import (
    SparkSilverTelemetryProcessor,
)
from ac_race_engineer.spark.sql_analytics import (
    SparkSQLSessionAnalyzer,
)


def main():

    bronze_files = list(
        Path(
            "data/bronze/telemetry"
        ).glob(
            "**/telemetry.parquet"
        )
    )

    if not bronze_files:
        raise FileNotFoundError(
            "No Bronze telemetry found"
        )

    latest_bronze = max(
        bronze_files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    spark = create_spark_session(
        app_name=(
            "AC Race Engineer "
            "Spark SQL"
        )
    )

    try:

        pandas_processor = (
            SilverTelemetryProcessor()
        )

        spark_processor = (
            SparkSilverTelemetryProcessor(
                spark=spark
            )
        )

        pandas_result = (
            pandas_processor.process(
                latest_bronze
            )
        )

        spark_result = (
            spark_processor.process(
                latest_bronze
            )
        )

        analyzer = (
            SparkSQLSessionAnalyzer(
                spark=spark
            )
        )

        summary = analyzer.analyze(
            spark_result.output_path
        )

        validator = (
            SilverParityValidator(
                spark=spark
            )
        )

        parity = validator.validate(
            pandas_silver_file=(
                pandas_result.output_file
            ),
            spark_silver_path=(
                spark_result.output_path
            ),
        )

        print()
        print("SPARK SQL ANALYTICS")
        print("===================")
        print()

        print(
            f"Session: "
            f"{summary.session_id}"
        )

        print(
            f"Samples: "
            f"{summary.sample_count}"
        )

        print(
            f"Duration: "
            f"{summary.duration_seconds:.2f} s"
        )

        print(
            f"Max speed: "
            f"{summary.maximum_speed_kmh:.2f} km/h"
        )

        print(
            f"Average speed: "
            f"{summary.average_speed_kmh:.2f} km/h"
        )

        print(
            "Front pressure: "
            f"{summary.average_front_pressure_psi:.2f} psi"
        )

        print(
            "Rear pressure: "
            f"{summary.average_rear_pressure_psi:.2f} psi"
        )

        print(
            "Front slip: "
            f"{summary.average_front_slip_angle_deg:.3f} deg"
        )

        print(
            "Rear slip: "
            f"{summary.average_rear_slip_angle_deg:.3f} deg"
        )

        print()
        print("PANDAS vs SPARK")
        print("===============")
        print()

        print(
            f"Pandas rows: "
            f"{parity.pandas_rows}"
        )

        print(
            f"Spark rows: "
            f"{parity.spark_rows}"
        )

        print(
            f"Row count: "
            f"{parity.row_count_match}"
        )

        print(
            f"Sample indices: "
            f"{parity.sample_index_match}"
        )

        print(
            f"Metrics: "
            f"{parity.all_metrics_match}"
        )

        print(
            "Maximum difference: "
            f"{parity.max_absolute_difference:.10f}"
        )

        print()

        print(
            "PARITY: "
            + (
                "PASSED"
                if parity.parity_passed
                else "FAILED"
            )
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

