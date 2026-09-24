from dataclasses import dataclass
from typing import Any

from ac_race_engineer.kafka.telemetry import (
    KafkaTelemetryPublisher,
    frame_to_payload,
)


@dataclass
class FakeFrame:
    speed_kph: float
    rpm: float
    gear: int


class FakeKafkaProducer:
    def __init__(self) -> None:
        self.messages: list[
            dict[str, Any]
        ] = []

    def publish_json(
        self,
        *,
        topic: str,
        payload: dict[str, Any],
        key: str | None = None,
    ) -> None:
        self.messages.append(
            {
                "topic": topic,
                "payload": payload,
                "key": key,
            }
        )

    def flush(
        self,
        timeout: float = 10.0,
    ) -> int:
        return 0


def test_frame_to_payload() -> None:
    frame = FakeFrame(
        speed_kph=120.5,
        rpm=6500.0,
        gear=4,
    )

    payload = frame_to_payload(frame)

    assert payload == {
        "speed_kph": 120.5,
        "rpm": 6500.0,
        "gear": 4,
    }


def test_publish_frame() -> None:
    producer = FakeKafkaProducer()

    publisher = KafkaTelemetryPublisher(
        producer=producer,
    )

    publisher.publish_frame(
        session_id="session-001",
        frame=FakeFrame(
            speed_kph=120.5,
            rpm=6500.0,
            gear=4,
        ),
    )

    assert len(producer.messages) == 1

    message = producer.messages[0]

    assert message["topic"] == "telemetry.raw"
    assert message["key"] == "session-001"

    payload = message["payload"]

    assert payload["session_id"] == "session-001"
    assert payload["source"] == "simulator"
    assert payload["schema_version"] == 1
    assert payload["speed_kph"] == 120.5


def test_publish_frames() -> None:
    producer = FakeKafkaProducer()

    publisher = KafkaTelemetryPublisher(
        producer=producer,
    )

    frames = [
        FakeFrame(
            speed_kph=100.0,
            rpm=5000.0,
            gear=3,
        ),
        FakeFrame(
            speed_kph=110.0,
            rpm=5500.0,
            gear=4,
        ),
        FakeFrame(
            speed_kph=120.0,
            rpm=6000.0,
            gear=4,
        ),
    ]

    count = publisher.publish_frames(
        session_id="session-002",
        frames=frames,
    )

    assert count == 3
    assert len(producer.messages) == 3

    assert [
        item["payload"]["sequence"]
        for item in producer.messages
    ] == [
        0,
        1,
        2,
    ]

    assert all(
        item["key"] == "session-002"
        for item in producer.messages
    )