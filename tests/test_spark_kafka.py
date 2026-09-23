import json
from datetime import UTC

import pytest

from ac_race_engineer.kafka.messages import KafkaTelemetryMessage
from ac_race_engineer.spark.kafka import (
    KafkaTelemetryStream,
    decode_kafka_records,
    kafka_record_schema,
)
from ac_race_engineer.spark.session import create_spark_session
from ac_race_engineer.telemetry.simulator import SimulatorSource


@pytest.fixture(scope="module")
def spark():
    session = create_spark_session(app_name="kafka-decoding-tests", master="local[2]")
    yield session
    session.stop()


def test_kafka_flattening_and_quality_preserve_telemetry(tmp_path, spark):
    frame = SimulatorSource(seed=42).read_frame()
    message = KafkaTelemetryMessage(source="simulator", setup_id="baseline", frame=frame)
    records = spark.createDataFrame(
        [(message.key, message.encode(), "telemetry.raw", 2, 37, frame.timestamp)],
        kafka_record_schema(),
    )
    decoded = decode_kafka_records(records)
    row = decoded.first()
    assert row.timestamp.astimezone(UTC) == frame.timestamp
    assert row.session_id == frame.session_id
    assert row.setup_id == "baseline"
    assert row.vehicle_speed_kmh == frame.vehicle.speed_kmh
    assert row.fl_pressure_psi == frame.wheels["FL"].pressure_psi
    assert row.source_file == "kafka://telemetry.raw/2/37"
    assert row.kafka_value == message.encode()
    assert row.kafka_message_error is None
    stream = KafkaTelemetryStream(spark, output_directory=tmp_path / "stream")
    enriched = stream.downstream.transform(decoded).first()
    assert enriched.is_valid
    assert enriched.front_pressure_psi == pytest.approx(
        (frame.wheels["FL"].pressure_psi + frame.wheels["FR"].pressure_psi) / 2
    )


@pytest.mark.parametrize(
    "case,expected",
    [
        ("json", "invalid_json"),
        ("version", "unsupported_schema"),
        ("source", "invalid_metadata"),
        ("key", "invalid_metadata"),
        ("tombstone", "invalid_json"),
    ],
)
def test_bad_messages_are_preserved_and_quarantined(tmp_path, spark, case, expected):
    message = KafkaTelemetryMessage(source="simulator", frame=SimulatorSource(seed=42).read_frame())
    data = message.model_dump(mode="json")
    key = message.key
    if case == "version":
        data["schema_version"] = 99
    if case == "source":
        data["source"] = None
    if case == "key":
        key = b"wrong-session"
    value = json.dumps(data).encode()
    if case == "json":
        value = b"{broken-json"
    if case == "tombstone":
        value = None
    records = spark.createDataFrame(
        [(key, value, "telemetry.raw", 0, 4, message.frame.timestamp)], kafka_record_schema()
    )
    stream = KafkaTelemetryStream(spark, output_directory=tmp_path / "stream")
    row = stream.downstream.transform(decode_kafka_records(records)).first()
    assert row.kafka_message_error == expected
    assert row.kafka_value == value
    assert not row.is_valid
    assert row.quality_invalid_message
    assert row.quality_issue_count >= 1


def test_invalid_event_time_does_not_crash_the_stream(tmp_path, spark):
    message = KafkaTelemetryMessage(source="simulator", frame=SimulatorSource(seed=42).read_frame())
    data = message.model_dump(mode="json")
    data["frame"]["timestamp"] = "not-a-date"
    records = spark.createDataFrame(
        [(message.key, json.dumps(data).encode(), "telemetry.raw", 0, 5, message.frame.timestamp)],
        kafka_record_schema(),
    )
    stream = KafkaTelemetryStream(spark, output_directory=tmp_path / "stream")
    row = stream.downstream.transform(decode_kafka_records(records)).first()
    assert row.timestamp is None
    assert row.quality_missing_required
    assert not row.is_valid
