import shutil
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

OUTPUT = Path(
    "/workspace/ac-race-engineer/data/docker-smoke/parquet"
)


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)

    spark = (
        SparkSession.builder
        .appName("docker-lakehouse-smoke")
        .getOrCreate()
    )

    try:
        dataframe = (
            spark.range(100)
            .withColumn(
                "session_id",
                F.lit("docker-session-001"),
            )
            .withColumn(
                "speed_kph",
                F.col("id") * 1.5,
            )
        )

        dataframe.write.mode(
            "overwrite"
        ).parquet(
            str(OUTPUT)
        )

        result = spark.read.parquet(
            str(OUTPUT)
        )

        print(
            "PARQUET ROW COUNT =",
            result.count(),
        )

        print(
            "PARQUET COLUMNS =",
            result.columns,
        )

        result.orderBy("id").show(
            5,
            truncate=False,
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

