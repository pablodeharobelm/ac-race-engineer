import os
import sys

from pyspark.sql import SparkSession


def create_spark_session(
    app_name: str = "ac-race-engineer",
    master: str = "local[*]",
) -> SparkSession:

    python_executable = sys.executable

    os.environ[
        "PYSPARK_PYTHON"
    ] = python_executable

    os.environ[
        "PYSPARK_DRIVER_PYTHON"
    ] = python_executable

    os.environ.setdefault(
        "SPARK_LOCAL_IP",
        "127.0.0.1",
    )

    spark = (
        SparkSession.builder
        .appName(
            app_name
        )
        .master(
            master
        )
        .config(
            "spark.ui.enabled",
            "false",
        )
        .config(
            "spark.sql.session.timeZone",
            "UTC",
        )
        .config(
            "spark.sql.shuffle.partitions",
            "4",
        )
        .config(
            "spark.pyspark.python",
            python_executable,
        )
        .config(
            "spark.pyspark.driver.python",
            python_executable,
        )
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel(
        "WARN"
    )

    return spark