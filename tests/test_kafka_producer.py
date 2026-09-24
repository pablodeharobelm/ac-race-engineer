import json
from datetime import UTC, datetime
from typing import Any

from ac_race_engineer.kafka import (
    KafkaProducer,
    serialize_json,
)


class FakeProducer:
    def __init__(self) -> None:
        self.messages: list[
            dict[str, Any]
        ] = []

        self.poll_calls = 0
        self.flush_calls = 0

    def produce(
        self,
        *,
        topic: str,
        key: bytes | None,
        value: bytes,
        on_delivery: Any,
    ) -> None:
        self.messages.append(
            {
                "topic": topic,
                "key": key,
                "value": value,
                "on_delivery": on_delivery,
            }
        )

    def poll(
        self,
        timeout: float,
    ) -> None:
        self.poll_calls += 1

    def flush(
        self,
        timeout: float,
    ) -> int:
        self.flush_calls += 1
        return 0


def test_serialize_json() -> None:
    payload = {
        "session_id": "test-001",
        "speed_kph": 120.5,
        "rpm": 6500,
    }

    result = serialize_json(
        payload
    )

    decoded = json.loads(
        result.decode("utf-8")
    )

    assert decoded == payload


def test_serialize_datetime() -> None:
    timestamp = datetime(
        2026,
        9,
        24,
        16,
        30,
        tzinfo=UTC,
    )

    result = serialize_json(
        {
            "timestamp": timestamp,
        }
    )

    decoded = json.loads(
        result.decode("utf-8")
    )

    assert decoded[
        "timestamp"
    ] == timestamp.isoformat()


def test_publish_json() -> None:
    fake = FakeProducer()

    producer = KafkaProducer(
        producer=fake
    )

    producer.publish_json(
        topic="telemetry.raw",
        key="session-001",
        payload={
            "session_id": "session-001",
            "speed_kph": 123.4,
        },
    )

    assert len(
        fake.messages
    ) == 1

    message = fake.messages[0]

    assert (
        message["topic"]
        == "telemetry.raw"
    )

    assert (
        message["key"]
        == b"session-001"
    )

    payload = json.loads(
        message["value"].decode(
            "utf-8"
        )
    )

    assert payload[
        "speed_kph"
    ] == 123.4

    assert fake.poll_calls == 1


def test_flush() -> None:
    fake = FakeProducer()

    producer = KafkaProducer(
        producer=fake
    )

    remaining = producer.flush()

    assert remaining == 0
    assert fake.flush_calls == 1