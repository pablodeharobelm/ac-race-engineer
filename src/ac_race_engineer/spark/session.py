import os
import sys

from pyspark import __version__ as pyspark_version
from pyspark.sql import SparkSession


def create_spark_session(
    app_name: str = "ac-race-engineer",
    master: str = "local[*]",
    *,
    enable_kafka: bool = False,
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

    builder = SparkSession.builder
    if enable_kafka:
        if SparkSession.getActiveSession() is not None:
            raise RuntimeError("Kafka must be enabled before creating the first Spark session")
        builder = builder.config(
            "spark.jars.packages",
            f"org.apache.spark:spark-sql-kafka-0-10_2.13:{pyspark_version}",
        )

    spark = (
        builder
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