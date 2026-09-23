from datetime import UTC, datetime, timedelta

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ac_race_engineer.lakehouse.silver import SilverTelemetryProcessor
from ac_race_engineer.spark.session import create_spark_session
from ac_race_engineer.spark.streaming import SparkTelemetryStream
from ac_race_engineer.storage.stream_publisher import TelemetryStreamPublisher
from ac_race_engineer.telemetry.simulator import SimulatorSource


@pytest.fixture(scope="module")
def spark():
    session = create_spark_session(app_name="streaming-tests", master="local[2]")
    yield session
    session.stop()


def make_input(tmp_path, spark):
    seed = TelemetryStreamPublisher(
        SimulatorSource(seed=42), tmp_path / "seed", setup_id="stream-test"
    ).publish(1)
    table = pq.ParquetFile(seed).read()
    schema = spark.read.parquet(str(seed)).schema
    inbox = tmp_path / "input"
    inbox.mkdir()
    return inbox, schema, table


def write_chunk(inbox, table, name, rows):
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), inbox / f"{name}.parquet")


def test_streaming_parity_checkpoints_deduplication_and_late_events(tmp_path, spark):
    inbox, schema, table = make_input(tmp_path, spark)
    base = table.to_pylist()[0]
    epoch = datetime(2026, 9, 23, 12, tzinfo=UTC)

    def row(index, seconds, **changes):
        return {
            **base,
            "sample_index": index,
            "timestamp": epoch + timedelta(seconds=seconds),
            "elapsed_seconds": float(seconds),
            **changes,
        }

    first = row(0, 1, vehicle_speed_kmh=80.0)
    second = row(1, 3, vehicle_speed_kmh=120.0)
    invalid = row(2, 4, vehicle_throttle=2.0)
    missing = row(3, 4, timestamp=None, vehicle_throttle=None)
    write_chunk(inbox, table, "a", [first, invalid])
    write_chunk(inbox, table, "b", [first, second, missing])
    output = tmp_path / "stream"
    stream = SparkTelemetryStream(spark, inbox, schema, output)
    progress = stream.run_available()
    assert set(progress) == {"quality", "silver", "analytics"}
    assert spark.read.parquet(str(stream.paths["quality"])).count() == 5
    silver = spark.read.parquet(str(stream.paths["silver"]))
    assert silver.count() == 2
    quarantine = stream.read_quarantine()
    assert quarantine.count() == 2
    assert quarantine.filter("quality_issue_count IS NULL OR is_valid IS NULL").count() == 0
    assert quarantine.filter("timestamp IS NULL").count() == 1

    # Existing pandas Silver supplies an independent batch oracle for valid features.
    batch_input = tmp_path / "batch.parquet"
    pq.write_table(
        pa.Table.from_pylist([first, first, second, invalid, missing], schema=table.schema),
        batch_input,
    )
    pandas_result = SilverTelemetryProcessor(tmp_path / "pandas").process(batch_input)
    expected = pd.read_parquet(pandas_result.output_file).sort_values("sample_index")
    actual = silver.toPandas().sort_values("sample_index")
    assert set(actual.columns) == set(expected.columns)
    for column in expected.select_dtypes(include="number").columns:
        assert actual[column].tolist() == pytest.approx(expected[column].tolist(), abs=1e-6)

    # A fresh controller resumes the same offsets and state without replaying outputs.
    stream = SparkTelemetryStream(spark, inbox, schema, output)
    stream.run_available()
    assert spark.read.parquet(str(stream.paths["silver"])).count() == 2
    assert spark.read.parquet(str(stream.paths["quality"])).count() == 5

    # Out of order but within the watermark is accepted. A newer event closes the old window.
    within_delay = row(4, 2, vehicle_speed_kmh=100.0)
    write_chunk(inbox, table, "c", [within_delay])
    write_chunk(inbox, table, "d", [row(5, 40)])
    stream.run_available()
    windows = spark.read.parquet(str(stream.paths["analytics"]))
    closed = windows.filter("sample_count = 3").collect()
    assert len(closed) == 1
    assert closed[0]["average_speed_kmh"] == pytest.approx(100.0)
    assert closed[0]["maximum_speed_kmh"] == pytest.approx(120.0)
    assert closed[0]["start"].astimezone(UTC) == epoch
    assert closed[0]["end"].astimezone(UTC) == epoch + timedelta(seconds=10)

    # This new sample is older than the persisted watermark; it stays in the audit only.
    write_chunk(inbox, table, "e", [row(6, 1, vehicle_speed_kmh=900.0)])
    write_chunk(inbox, table, "f", [row(7, 80)])
    stream.run_available()
    silver = spark.read.parquet(str(stream.paths["silver"]))
    assert {item.sample_index for item in silver.select("sample_index").collect()} == {
        0,
        1,
        4,
        5,
        7,
    }
    assert spark.read.parquet(str(stream.paths["quality"])).count() == 9
    assert stream.read_quarantine().count() == 2
    windows = spark.read.parquet(str(stream.paths["analytics"]))
    assert windows.count() == 2  # The window containing t=80 is still open.
    assert windows.filter("sample_count = 3").first()["average_speed_kmh"] == pytest.approx(100.0)

    with pytest.raises(ValueError, match="configuration changed"):
        SparkTelemetryStream(spark, inbox, schema, output, window_seconds=20).run_available()
    assert not spark.streams.active


def test_live_microbatches_stop_without_stopping_spark(tmp_path, spark):
    inbox, schema, table = make_input(tmp_path, spark)
    stream = SparkTelemetryStream(spark, inbox, schema, tmp_path / "stream")
    running = stream.start(trigger_seconds=1)
    try:
        assert all(query.isActive for query in running.queries.values())
        write_chunk(inbox, table, "live", table.to_pylist())
        running.drain()
        assert spark.read.parquet(str(stream.paths["silver"])).count() == 1
    finally:
        running.stop()
    assert not any(query.isActive for query in running.queries.values())
    assert spark.range(1).count() == 1


@pytest.mark.parametrize(
    "options",
    [
        {"watermark_seconds": 0},
        {"window_seconds": -1},
        {"max_files_per_trigger": 0},
    ],
)
def test_streaming_rejects_invalid_limits(tmp_path, options):
    with pytest.raises(ValueError, match="positive integer"):
        SparkTelemetryStream(None, tmp_path, None, tmp_path / "out", **options)


def test_streaming_rejects_nested_input_output(tmp_path):
    with pytest.raises(ValueError, match="non-nested"):
        SparkTelemetryStream(None, tmp_path, None, tmp_path / "out")


def test_shared_quality_matches_pandas_for_missing_numeric_values(tmp_path, spark):
    from ac_race_engineer.spark.silver import SparkSilverTelemetryProcessor

    _, _, table = make_input(tmp_path, spark)
    base = table.to_pylist()[0]
    rows = [
        {**base, "sample_index": 0, "vehicle_throttle": None},
        {**base, "sample_index": 1, "environment_grip_level": None},
        {**base, "sample_index": 2, "vehicle_speed_kmh": float("nan")},
        {**base, "sample_index": 3, "fl_pressure_psi": None},
    ]
    source = tmp_path / "missing.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), source)
    pandas_processor = SilverTelemetryProcessor(tmp_path / "pandas")
    expected = pandas_processor._add_quality_flags(pd.read_parquet(source))
    actual = SparkSilverTelemetryProcessor.transform(
        spark.read.parquet(str(source))
    ).toPandas().sort_values("sample_index")
    columns = [column for column in expected if column.startswith("quality_")] + ["is_valid"]
    for column in columns:
        assert actual[column].tolist() == expected[column].tolist()
    assert not actual["is_valid"].any()
