from pyspark.sql import functions as F

from ac_race_engineer.spark.session import (
    create_spark_session,
)


def test_spark_session_and_dataframe():

    spark = create_spark_session(
        app_name="ac-race-engineer-test",
        master="local[2]",
    )

    try:
        dataframe = spark.createDataFrame(
            [
                (1, 80.0),
                (2, 120.0),
                (3, 150.0),
            ],
            [
                "sample_index",
                "speed_kmh",
            ],
        )

        fast_samples = dataframe.filter(
            F.col("speed_kmh") > 100
        )

        assert dataframe.count() == 3
        assert fast_samples.count() == 2

        maximum_speed = (
            dataframe
            .agg(
                F.max(
                    "speed_kmh"
                ).alias(
                    "maximum_speed"
                )
            )
            .first()
        )

        assert (
            maximum_speed[
                "maximum_speed"
            ]
            == 150.0
        )

    finally:
        spark.stop()