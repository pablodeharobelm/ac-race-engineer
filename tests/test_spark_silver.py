from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ac_race_engineer.domain.session import (
    SessionType,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
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
        app_name="spark-silver-tests",
        master="local[2]",
    )

    yield session

    session.stop()


def create_bronze(
    tmp_path,
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
        setup_id="setup-spark",
    )

    ingestor = BronzeTelemetryIngestor(
        output_directory=(
            tmp_path
            / "bronze"
            / "telemetry"
        ),
    )

    result = ingestor.ingest(
        raw_file
    )

    return Path(
        result.output_file
    )


def test_spark_silver_creates_dataset(
    tmp_path,
    spark,
):

    bronze_file = create_bronze(
        tmp_path
    )

    processor = SparkSilverTelemetryProcessor(
        spark=spark,
        output_directory=(
            tmp_path
            / "silver_spark"
        ),
    )

    result = processor.process(
        bronze_file
    )

    assert result.status == "written"
    assert result.input_rows == 100
    assert result.output_rows == 100
    assert result.quarantined_rows == 0

    assert Path(
        result.output_path
    ).exists()


def test_spark_silver_adds_features(
    tmp_path,
    spark,
):

    bronze_file = create_bronze(
        tmp_path
    )

    processor = SparkSilverTelemetryProcessor(
        spark=spark,
        output_directory=(
            tmp_path
            / "silver_spark"
        ),
    )

    result = processor.process(
        bronze_file
    )

    dataframe = spark.read.parquet(
        result.output_path
    )

    expected_columns = {
        "vehicle_speed_mps",
        "front_pressure_psi",
        "rear_pressure_psi",
        "front_core_temp_c",
        "rear_core_temp_c",
        "front_brake_temp_c",
        "rear_brake_temp_c",
        "front_suspension_travel_mm",
        "rear_suspension_travel_mm",
        "front_slip_angle_deg",
        "rear_slip_angle_deg",
        "left_right_load_delta_n",
        "quality_issue_count",
        "is_valid",
    }

    assert expected_columns.issubset(
        set(
            dataframe.columns
        )
    )


def test_spark_silver_quarantines_invalid_row(
    tmp_path,
    spark,
):

    bronze_file = create_bronze(
        tmp_path
    )

    table = pq.read_table(
        bronze_file
    )

    dataframe = table.to_pandas()

    dataframe.loc[
        0,
        "vehicle_throttle",
    ] = 1.5

    pq.write_table(
        pa.Table.from_pandas(
            dataframe,
            preserve_index=False,
        ),
        bronze_file,
    )

    processor = SparkSilverTelemetryProcessor(
        spark=spark,
        output_directory=(
            tmp_path
            / "silver_spark"
        ),
    )

    result = processor.process(
        bronze_file
    )

    assert result.output_rows == 99
    assert result.quarantined_rows == 1

    assert result.quarantine_path is not None

    quarantine = spark.read.parquet(
        result.quarantine_path
    )

    assert quarantine.count() == 1

    row = quarantine.first()

    assert row[
        "quality_invalid_controls"
    ]


def test_spark_silver_is_idempotent(
    tmp_path,
    spark,
):

    bronze_file = create_bronze(
        tmp_path
    )

    processor = SparkSilverTelemetryProcessor(
        spark=spark,
        output_directory=(
            tmp_path
            / "silver_spark"
        ),
    )

    first = processor.process(
        bronze_file
    )

    second = processor.process(
        bronze_file
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