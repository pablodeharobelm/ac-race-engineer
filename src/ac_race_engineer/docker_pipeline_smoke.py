import argparse
from pathlib import Path

from ac_race_engineer.spark.pipeline import (
    SparkLakehousePipeline,
)
from ac_race_engineer.spark.session import (
    create_spark_session,
)

ROOT = Path(
    "/workspace/ac-race-engineer"
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "raw_file",
        type=Path,
    )

    args = parser.parse_args()

    if not args.raw_file.exists():
        raise FileNotFoundError(
            args.raw_file
        )

    spark = create_spark_session(
        app_name="docker-lakehouse-pipeline",
        master="spark://spark-master:7077",
    )

    try:
        pipeline = SparkLakehousePipeline(
            spark=spark,
            bronze_directory=(
                ROOT
                / "data/bronze/telemetry"
            ),
            silver_directory=(
                ROOT
                / "data/silver_spark"
            ),
            gold_directory=(
                ROOT
                / "data/gold_spark/session_summary"
            ),
        )

        result = pipeline.run(
            args.raw_file
        )

        print()
        print(
            "DOCKER LAKEHOUSE PIPELINE"
        )
        print(
            "========================="
        )
        print(
            f"Session: {result.session_id}"
        )
        print(
            f"Status: {result.status}"
        )

        for stage in result.stages:
            print()
            print(
                f"{stage.stage.upper()}: "
                f"{stage.status}"
            )
            print(
                f"Input: {stage.input_path}"
            )
            print(
                f"Output: {stage.output_path}"
            )
            print(
                f"Rows: {stage.output_rows}"
            )
            print(
                "Duration: "
                f"{stage.duration_seconds:.3f}s"
            )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

