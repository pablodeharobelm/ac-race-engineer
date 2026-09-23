from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from ac_race_engineer.kafka.client import KafkaTelemetryProducer, validate_topic
from ac_race_engineer.kafka.messages import KafkaTelemetryMessage
from ac_race_engineer.telemetry.simulator import SimulatorSource


def test_kafka_message_round_trip_and_partition_key():
    frame = SimulatorSource(seed=42).read_frame()
    message = KafkaTelemetryMessage(source="simulator", setup_id="setup", frame=frame)
    assert KafkaTelemetryMessage.model_validate_json(message.encode()) == message
    assert message.key == frame.session_id.encode()
    assert message.frame.timestamp == frame.timestamp
    with pytest.raises(ValidationError):
        KafkaTelemetryMessage.model_validate({**message.model_dump(), "schema_version": 99})


@pytest.mark.parametrize("topic", ["", ".", "..", "has space", "bad/topic", "x" * 250])
def test_rejects_invalid_topic(topic):
    with pytest.raises(ValueError, match="topic"):
        validate_topic(topic)


def test_producer_waits_for_acknowledgement():
    client = Mock()
    client.flush.return_value = 0
    frame = SimulatorSource(seed=42).read_frame()
    producer = KafkaTelemetryProducer(client=client)
    producer.send(frame)
    sent = client.produce.call_args
    assert sent.args == ("telemetry.raw",)
    assert sent.kwargs["key"] == frame.session_id.encode()
    assert KafkaTelemetryMessage.model_validate_json(sent.kwargs["value"]).frame == frame
    assert producer.delivered_count == 0
    sent.kwargs["on_delivery"](None, Mock())
    assert producer.flush() == 1


def test_producer_surfaces_timeout_and_delivery_failure():
    client = Mock()
    client.flush.return_value = 1
    producer = KafkaTelemetryProducer(client=client)
    with pytest.raises(TimeoutError, match="undelivered"):
        producer.flush(0.1)
    client.flush.return_value = 0
    producer.send(SimulatorSource(seed=42).read_frame())
    client.produce.call_args.kwargs["on_delivery"]("broker unavailable", Mock())
    with pytest.raises(RuntimeError, match="broker unavailable"):
        producer.flush()


def test_producer_does_not_hide_full_queue():
    client = Mock()
    client.produce.side_effect = BufferError("queue full")
    with pytest.raises(BufferError, match="queue full"):
        KafkaTelemetryProducer(client=client).send(SimulatorSource(seed=42).read_frame())
