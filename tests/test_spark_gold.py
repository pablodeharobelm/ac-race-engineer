
import pandas as pd
import pytest

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
)
from ac_race_engineer.lakehouse.gold import (
    GoldSessionAggregator,
)
from ac_race_engineer.lakehouse.silver import (
    SilverTelemetryProcessor,
)
from ac_race_engineer.spark.gold import (
    SparkGoldSessionAggregator,
)
from ac_race_engineer.spark.session import (
    create_spark_session,
)
from ac_race_engineer.spark.silver import (
    SparkSilverTelemetryProcessor,
)
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


@pytest.fixture(scope="module")
def spark():

    session = create_spark_session(
        app_name="spark-gold-tests",
        master="local[2]",
    )

    yield session

    session.stop()


def build_layers(
    tmp_path,
    spark,
):

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=(
            tmp_path / "raw"
        ),
    )

    raw_file = recorder.record_samples(
        sample_count=150,
        session_type=SessionType.TEST,
        setup_id="setup-spark-gold",
    )

    bronze = BronzeTelemetryIngestor(
        output_directory=(
            tmp_path
            / "bronze"
            / "telemetry"
        )
    )

    bronze_result = bronze.ingest(
        raw_file
    )

    pandas_silver = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path
                / "silver_pandas"
            )
        )
    )

    pandas_silver_result = (
        pandas_silver.process(
            bronze_result.output_file
        )
    )

    spark_silver = (
        SparkSilverTelemetryProcessor(
            spark=spark,
            output_directory=(
                tmp_path
                / "silver_spark"
            ),
        )
    )

    spark_silver_result = (
        spark_silver.process(
            bronze_result.output_file
        )
    )

    pandas_gold = (
        GoldSessionAggregator(
            output_directory=(
                tmp_path
                / "gold_pandas"
            )
        )
    )

    pandas_gold_result = (
        pandas_gold.aggregate(
            pandas_silver_result.output_file
        )
    )

    spark_gold = (
        SparkGoldSessionAggregator(
            spark=spark,
            output_directory=(
                tmp_path
                / "gold_spark"
            ),
        )
    )

    spark_gold_result = (
        spark_gold.aggregate(
            spark_silver_result.output_path
        )
    )

    return (
        pandas_gold_result,
        spark_gold_result,
    )


def test_spark_gold_creates_single_row(
    tmp_path,
    spark,
):

    _, spark_result = build_layers(
        tmp_path,
        spark,
    )

    assert spark_result.status == "written"

    assert (
        spark_result.source_rows
        == 150
    )

    assert (
        spark_result.output_rows
        == 1
    )

    dataframe = spark.read.parquet(
        spark_result.output_path
    )

    assert dataframe.count() == 1


def test_spark_gold_metrics(
    tmp_path,
    spark,
):

    _, spark_result = build_layers(
        tmp_path,
        spark,
    )

    row = (
        spark
        .read
        .parquet(
            spark_result.output_path
        )
        .first()
    )

    assert row is not None

    assert (
        row["sample_count"]
        == 150
    )

    assert (
        row["maximum_speed_kmh"]
        > 0
    )

    assert (
        row["average_speed_kmh"]
        > 0
    )

    assert (
        row[
            "average_front_pressure_psi"
        ]
        > 0
    )

    assert (
        row[
            "average_front_core_temp_c"
        ]
        > 0
    )

    assert (
        row["fuel_used_l"]
        >= 0
    )

    assert (
        row["valid_row_percentage"]
        == pytest.approx(
            100.0
        )
    )


def test_spark_gold_is_idempotent(
    tmp_path,
    spark,
):

    simulator = SimulatorSource(
        hz=20,
        seed=42,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=(
            tmp_path / "raw"
        ),
    )

    raw_file = recorder.record_samples(
        sample_count=100,
        session_type=SessionType.TEST,
        setup_id="setup-idempotency",
    )

    bronze = BronzeTelemetryIngestor(
        output_directory=(
            tmp_path
            / "bronze"
            / "telemetry"
        )
    )

    bronze_result = bronze.ingest(
        raw_file
    )

    spark_silver = (
        SparkSilverTelemetryProcessor(
            spark=spark,
            output_directory=(
                tmp_path
                / "silver_spark"
            ),
        )
    )

    silver_result = (
        spark_silver.process(
            bronze_result.output_file
        )
    )

    aggregator = (
        SparkGoldSessionAggregator(
            spark=spark,
            output_directory=(
                tmp_path
                / "gold_spark"
            ),
        )
    )

    first = aggregator.aggregate(
        silver_result.output_path
    )

    second = aggregator.aggregate(
        silver_result.output_path
    )

    assert first.status == "written"
    assert second.status == "skipped"

    assert (
        first.source_checksum
        == second.source_checksum
    )

    assert (
        first.output_path
        == second.output_path
    )


def test_spark_gold_matches_pandas_gold(
    tmp_path,
    spark,
):

    (
        pandas_result,
        spark_result,
    ) = build_layers(
        tmp_path,
        spark,
    )

    pandas_df = pd.read_parquet(
        pandas_result.output_file
    )

    spark_row = (
        spark
        .read
        .parquet(
            spark_result.output_path
        )
        .first()
    )

    assert len(pandas_df) == 1
    assert spark_row is not None

    pandas_row = pandas_df.iloc[
        0
    ]

    assert (
        str(
            pandas_row[
                "session_id"
            ]
        )
        == str(
            spark_row[
                "session_id"
            ]
        )
    )

    assert set(pandas_df.columns) == set(spark_row.asDict())

    metrics = [
        "sample_count",
        "peak_front_core_temp_c",
        "peak_rear_core_temp_c",
        "peak_front_brake_temp_c",
        "peak_rear_brake_temp_c",
        "maximum_front_suspension_travel_mm",
        "maximum_rear_suspension_travel_mm",
        "duration_seconds",
        "maximum_speed_kmh",
        "average_speed_kmh",
        "average_rpm",
        "average_throttle",
        "average_brake",
        "maximum_lateral_g",
        "maximum_braking_g",
        "fuel_used_l",
        "average_front_pressure_psi",
        "average_rear_pressure_psi",
        "average_front_core_temp_c",
        "average_rear_core_temp_c",
        "average_front_brake_temp_c",
        "average_rear_brake_temp_c",
        "average_front_suspension_travel_mm",
        "average_rear_suspension_travel_mm",
        "average_front_slip_angle_deg",
        "average_rear_slip_angle_deg",
        "average_front_rear_slip_delta_deg",
        "average_left_right_load_delta_n",
        "valid_row_percentage",
    ]

    for metric in metrics:

        assert float(
            spark_row[
                metric
            ]
        ) == pytest.approx(
            float(
                pandas_row[
                    metric
                ]
            ),
            abs=1e-6,
        )

def test_checksum_is_independent_of_row_order_and_partitions(spark):
    dataframe = spark.range(12).selectExpr("id", "id * 0.5 AS value")
    checksum = SparkGoldSessionAggregator._calculate_checksum
    assert checksum(dataframe) == checksum(
        dataframe.orderBy("id", ascending=False).repartition(3).select("value", "id")
    )
    assert checksum(dataframe) != checksum(dataframe.withColumnRenamed("value", "other"))
    assert checksum(dataframe) != checksum(dataframe.union(dataframe.limit(1)))
    assert checksum(dataframe) != checksum(dataframe.selectExpr("id", "value + 1 AS value"))


def test_checksum_distinguishes_null_positions(spark):
    checksum = SparkGoldSessionAggregator._calculate_checksum
    left = spark.sql("SELECT CAST(NULL AS BIGINT) AS a, 1L AS b")
    right = spark.sql("SELECT 1L AS a, CAST(NULL AS BIGINT) AS b")
    assert checksum(left) != checksum(right)


def test_checksum_rejects_empty_dataset(spark):
    with pytest.raises(ValueError, match="empty"):
        SparkGoldSessionAggregator._calculate_checksum(spark.range(0))


def test_gold_fuel_uses_timestamp_before_sample_index(spark):
    from pyspark.sql import functions as F

    dataframe = spark.range(2)
    for column in SparkGoldSessionAggregator.REQUIRED_COLUMNS - {"timestamp"}:
        dataframe = dataframe.withColumn(column, F.lit(1.0))
    dataframe = dataframe.withColumn(
        "timestamp", F.to_timestamp(F.lit("2026-09-23 12:00:00"))
        + F.expr("id * INTERVAL 1 SECOND")
    ).withColumn("sample_index", 1 - F.col("id")).withColumn(
        "vehicle_fuel_l", 30.0 - F.col("id")
    )
    row = SparkGoldSessionAggregator._build_summary(dataframe).first()
    assert row["fuel_used_l"] == pytest.approx(1.0)


@pytest.mark.parametrize("timestamp_type", ["TIMESTAMP", "TIMESTAMP_NTZ"])
def test_checksum_preserves_timestamp_microseconds(spark, timestamp_type):
    checksum = SparkGoldSessionAggregator._calculate_checksum
    first = spark.sql(
        f"SELECT CAST('2026-09-23 12:00:00.000001' AS {timestamp_type}) AS timestamp"
    )
    second = spark.sql(
        f"SELECT CAST('2026-09-23 12:00:00.000002' AS {timestamp_type}) AS timestamp"
    )
    assert checksum(first) != checksum(second)
