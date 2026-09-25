import argparse
from pathlib import Path

from ac_race_engineer.spark.pipeline import SparkLakehousePipeline, SparkLakehousePipelineError
from ac_race_engineer.spark.session import create_spark_session


def main():
    parser = argparse.ArgumentParser(description="Process RAW telemetry through Spark Gold")
    parser.add_argument("raw_file", type=Path)
    args = parser.parse_args()
    spark = create_spark_session(app_name="AC Race Engineer Spark Lakehouse")
    try:
        result = SparkLakehousePipeline(spark).run(args.raw_file)
        print(result.model_dump_json(indent=2))
    except SparkLakehousePipelineError as exc:
        print(exc.result.model_dump_json(indent=2))
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()


