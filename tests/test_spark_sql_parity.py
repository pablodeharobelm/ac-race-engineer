from pathlib import Path

import pandas as pd
import pytest

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
)
from ac_race_engineer.lakehouse.silver import (
    SilverTelemetryProcessor,
)
from ac_race_engineer.spark.parity import (
    SilverParityValidator,
)
from ac_race_engineer.spark.session import (
    create_spark_session,
)
from ac_race_engineer.spark.silver import (
    SparkSilverTelemetryProcessor,
)
from ac_race_engineer.spark.sql_analytics import (
    SparkSQLSessionAnalyzer,
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
        app_name=(
            "spark-sql-parity-tests"
        ),
        master="local[2]",
    )

    yield session

    session.stop()


def build_silver_layers(
    tmp_path,
    spark,
):

    simulator = SimulatorSource(
        seed=42,
        hz=20,
    )

    recorder = SessionRecorder(
        source=simulator,
        output_directory=(
            tmp_path / "raw"
        ),
    )

    raw_file = recorder.record_samples(
        sample_count=120,
        session_type=(
            SessionType.TEST
        ),
        setup_id="setup-parity",
    )

    bronze = (
        BronzeTelemetryIngestor(
            output_directory=(
                tmp_path
                / "bronze"
                / "telemetry"
            )
        )
    )

    bronze_result = bronze.ingest(
        raw_file
    )

    pandas_processor = (
        SilverTelemetryProcessor(
            output_directory=(
                tmp_path
                / "silver_pandas"
            )
        )
    )

    pandas_result = (
        pandas_processor.process(
            bronze_result.output_file
        )
    )

    spark_processor = (
        SparkSilverTelemetryProcessor(
            spark=spark,
            output_directory=(
                tmp_path
                / "silver_spark"
            ),
        )
    )

    spark_result = (
        spark_processor.process(
            bronze_result.output_file
        )
    )

    return (
        Path(
            pandas_result.output_file
        ),
        Path(
            spark_result.output_path
        ),
    )


def test_spark_sql_session_summary(
    tmp_path,
    spark,
):

    (
        _,
        spark_path,
    ) = build_silver_layers(
        tmp_path,
        spark,
    )

    analyzer = (
        SparkSQLSessionAnalyzer(
            spark=spark
        )
    )

    summary = analyzer.analyze(
        spark_path
    )

    assert summary.sample_count == 120

    assert (
        summary.maximum_speed_kmh
        > 0
    )

    assert (
        summary.average_speed_kmh
        > 0
    )

    assert (
        summary.average_front_pressure_psi
        > 0
    )

    assert (
        summary.average_front_core_temp_c
        > 0
    )

    assert (
        summary.valid_row_percentage
        == pytest.approx(
            100.0
        )
    )


def test_pandas_and_spark_have_parity(
    tmp_path,
    spark,
):

    (
        pandas_file,
        spark_path,
    ) = build_silver_layers(
        tmp_path,
        spark,
    )

    validator = SilverParityValidator(
        spark=spark,
        tolerance=1e-6,
    )

    report = validator.validate(
        pandas_silver_file=(
            pandas_file
        ),
        spark_silver_path=(
            spark_path
        ),
    )

    assert report.row_count_match
    assert report.sample_index_match
    assert report.all_metrics_match
    assert report.parity_passed

    assert (
        report.pandas_rows
        == 120
    )

    assert (
        report.spark_rows
        == 120
    )


def test_parity_detects_modified_dataset(
    tmp_path,
    spark,
):

    (
        pandas_file,
        spark_path,
    ) = build_silver_layers(
        tmp_path,
        spark,
    )

    dataframe = pd.read_parquet(
        pandas_file
    )

    dataframe.loc[
        0,
        "vehicle_speed_kmh",
    ] += 50.0

    dataframe.to_parquet(
        pandas_file,
        index=False,
    )

    validator = SilverParityValidator(
        spark=spark,
        tolerance=1e-6,
    )

    report = validator.validate(
        pandas_silver_file=(
            pandas_file
        ),
        spark_silver_path=(
            spark_path
        ),
    )

    assert not report.all_metrics_match
    assert not report.parity_passed

    mismatches = [
        metric.metric
        for metric in report.metrics
        if not metric.within_tolerance
    ]

    assert (
        "maximum_speed_kmh"
        in mismatches
        or "average_speed_kmh"
        in mismatches
    )