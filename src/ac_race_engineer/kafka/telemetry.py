from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from ac_race_engineer.kafka.config import (
    get_telemetry_topic,
)
from ac_race_engineer.kafka.producer import (
    KafkaProducer,
)


def frame_to_payload(
    frame: Any,
) -> dict[str, Any]:
    model_dump = getattr(
        frame,
        "model_dump",
        None,
    )

    if callable(model_dump):
        result = model_dump()

        if not isinstance(result, dict):
            raise TypeError(
                "model_dump() must return a dictionary"
            )

        return result

    if is_dataclass(frame):
        result = asdict(frame)

        if not isinstance(result, dict):
            raise TypeError(
                "Telemetry dataclass must serialize "
                "to a dictionary"
            )

        return result

    if isinstance(frame, Mapping):
        return dict(frame)

    raise TypeError(
        "Unsupported telemetry frame type: "
        f"{type(frame).__name__}"
    )


class KafkaTelemetryPublisher:
    def __init__(
        self,
        *,
        producer: KafkaProducer,
        topic: str | None = None,
    ) -> None:
        self._producer = producer
        self._topic = (
            topic
            or get_telemetry_topic()
        )

    def publish_frame(
        self,
        *,
        session_id: str,
        frame: Any,
        source: str = "simulator",
        sequence: int | None = None,
    ) -> None:
        payload = frame_to_payload(frame)

        payload["session_id"] = session_id
        payload["source"] = source
        payload["schema_version"] = 1

        if sequence is not None:
            payload["sequence"] = sequence

        self._producer.publish_json(
            topic=self._topic,
            key=session_id,
            payload=payload,
        )

    def publish_frames(
        self,
        *,
        session_id: str,
        frames: Iterable[Any],
        source: str = "simulator",
    ) -> int:
        count = 0

        for sequence, frame in enumerate(frames):
            self.publish_frame(
                session_id=session_id,
                frame=frame,
                source=source,
                sequence=sequence,
            )

            count += 1

        remaining = self._producer.flush()

        if remaining != 0:
            raise RuntimeError(
                f"{remaining} Kafka telemetry "
                "messages were not delivered"
            )

        return count

