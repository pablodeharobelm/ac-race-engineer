"""Run explicitly in a fresh Python process with AC_KAFKA_BOOTSTRAP configured."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ac_race_engineer.kafka.client import (
    KafkaTelemetryProducer,
    consume_telemetry,
    create_telemetry_topic,
)
from ac_race_engineer.spark.kafka import KafkaTelemetryStream
from ac_race_engineer.spark.session import create_spark_session
from ac_race_engineer.telemetry.simulator import SimulatorSource

pytestmark = [
    pytest.mark.kafka_integration,
    pytest.mark.skipif(
        not os.environ.get("AC_KAFKA_BOOTSTRAP"),
        reason="Set AC_KAFKA_BOOTSTRAP to test a real broker",
    ),
]


def test_real_kafka_to_silver_and_checkpoint_restart(tmp_path):
    pytest.importorskip("confluent_kafka")
    bootstrap = os.environ["AC_KAFKA_BOOTSTRAP"]
    topic = "telemetry.test." + uuid4().hex
    create_telemetry_topic(bootstrap, topic, partitions=1)
    producer = KafkaTelemetryProducer(bootstrap, topic)
    simulator = SimulatorSource(seed=42)
    epoch = datetime(2026, 9, 23, 12, tzinfo=UTC)
    frames = [
        simulator.read_frame().model_copy(update={"timestamp": epoch + timedelta(seconds=i)})
        for i in range(3)
    ]
    for frame in frames:
        producer.send(frame)
    assert producer.flush() == 3
    inspected = list(consume_telemetry(bootstrap, topic, limit=3, timeout_seconds=30))
    assert [item.frame for item in inspected] == frames

    spark = create_spark_session(app_name="real-kafka-test", master="local[2]", enable_kafka=True)
    try:
        stream = KafkaTelemetryStream(spark, bootstrap, topic, tmp_path / "stream")
        stream.run_available()
        assert spark.read.parquet(str(stream.bronze_directory)).count() == 3
        assert spark.read.parquet(str(stream.downstream.paths["silver"])).count() == 3
        # Same checkpoint resumes without replay. A duplicate event has a new Kafka offset.
        producer.send(frames[0])
        producer.send(
            simulator.read_frame().model_copy(update={"timestamp": epoch + timedelta(seconds=40)})
        )
        assert producer.flush() == 5
        producer.client.produce(topic, key=b"bad", value=b"{malformed-json")
        producer.flush()
        resumed = KafkaTelemetryStream(spark, bootstrap, topic, tmp_path / "stream")
        resumed.run_available()
        bronze = spark.read.parquet(str(resumed.bronze_directory))
        assert bronze.count() == 6
        assert (
            bronze.select("kafka_topic", "kafka_partition", "kafka_offset").distinct().count() == 6
        )
        silver = spark.read.parquet(str(resumed.downstream.paths["silver"]))
        assert silver.count() == 4
        assert resumed.downstream.read_quarantine().count() == 1
        closed = spark.read.parquet(str(resumed.downstream.paths["analytics"])).first()
        assert closed.sample_count == 3
        assert closed.average_speed_kmh == pytest.approx(
            sum(frame.vehicle.speed_kmh for frame in frames) / 3
        )
        resumed.run_available()
        assert spark.read.parquet(str(resumed.bronze_directory)).count() == 6
        assert spark.read.parquet(str(resumed.downstream.paths["silver"])).count() == 4
    finally:
        spark.stop()
