from pyspark.sql import SparkSession


def main() -> None:
    spark = (
        SparkSession.builder
        .appName("docker-kafka-smoke")
        .getOrCreate()
    )

    try:
        dataframe = (
            spark.read
            .format("kafka")
            .option(
                "kafka.bootstrap.servers",
                "kafka:19092",
            )
            .option(
                "subscribe",
                "telemetry.raw",
            )
            .option(
                "startingOffsets",
                "earliest",
            )
            .option(
                "endingOffsets",
                "latest",
            )
            .load()
        )

        rows = dataframe.selectExpr(
            "CAST(key AS STRING) AS key",
            "CAST(value AS STRING) AS value",
            "topic",
            "partition",
            "offset",
        )

        print(
            "KAFKA ROW COUNT =",
            rows.count(),
        )

        rows.show(
            20,
            truncate=False,
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()

