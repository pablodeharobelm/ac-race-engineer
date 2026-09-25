import os
import sys
from pathlib import Path

import pyspark
from pyspark.sql import SparkSession


def create_spark_session(
    app_name: str = "ac-race-engineer",
    master: str = "local[*]",
    *,
    enable_kafka: bool = False,
) -> SparkSession:
    pyspark_version = pyspark.__version__

    python_executable = sys.executable

    os.environ["PYSPARK_PYTHON"] = python_executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = python_executable

    hadoop_home = Path(
        os.environ.get(
            "HADOOP_HOME",
            r"C:\hadoop",
        )
    )

    winutils = hadoop_home / "bin" / "winutils.exe"
    hadoop_dll = hadoop_home / "bin" / "hadoop.dll"

    if winutils.exists() and hadoop_dll.exists():
        os.environ["HADOOP_HOME"] = str(hadoop_home)

        hadoop_bin = str(hadoop_home / "bin")
        path_entries = os.environ.get(
            "PATH",
            "",
        ).split(os.pathsep)

        if hadoop_bin not in path_entries:
            os.environ["PATH"] = (
                hadoop_bin
                + os.pathsep
                + os.environ.get("PATH", "")
            )

    os.environ.setdefault(
        "SPARK_LOCAL_IP",
        "127.0.0.1",
    )

    builder = SparkSession.builder

    if enable_kafka:
        if SparkSession.getActiveSession() is not None:
            raise RuntimeError(
                "Kafka must be enabled before creating "
                "the first Spark session"
            )

        builder = builder.config(
            "spark.jars.packages",
            (
                "org.apache.spark:"
                "spark-sql-kafka-0-10_2.13:"
                f"{pyspark_version}"
            ),
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

