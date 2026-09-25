from pyspark.sql import SparkSession


def main() -> None:
    spark = (
        SparkSession.builder
        .appName("docker-smoke-test")
        .master("spark://spark-master:7077")
        .getOrCreate()
    )

    try:
        print("SPARK VERSION =", spark.version)
        print("COUNT =", spark.range(100).count())
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

