import json
import socket
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from confluent_kafka import Producer

from ac_race_engineer.kafka.config import (
    get_bootstrap_servers,
)


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Enum):
        return str(value.value)

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Path):
        return str(value)

    raise TypeError(
        f"Object of type {type(value).__name__} "
        "is not JSON serializable"
    )


def serialize_json(
    payload: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        default=_json_default,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class KafkaProducer:
    def __init__(
        self,
        *,
        bootstrap_servers: str | None = None,
        producer: Any | None = None,
    ) -> None:
        self._producer = producer or Producer(
            {
                "bootstrap.servers": (
                    bootstrap_servers
                    or get_bootstrap_servers()
                ),
                "client.id": (
                    f"ac-race-engineer-"
                    f"{socket.gethostname()}"
                ),
                "acks": "all",
            }
        )

    def publish_json(
        self,
        *,
        topic: str,
        payload: Mapping[str, Any],
        key: str | None = None,
    ) -> None:
        value = serialize_json(
            payload
        )

        encoded_key = (
            key.encode("utf-8")
            if key is not None
            else None
        )

        self._producer.produce(
            topic=topic,
            key=encoded_key,
            value=value,
            on_delivery=self._on_delivery,
        )

        self._producer.poll(0)

    def flush(
        self,
        timeout: float = 10.0,
    ) -> int:
        return int(
            self._producer.flush(
                timeout
            )
        )

    @staticmethod
    def _on_delivery(
        error: Any,
        message: Any,
    ) -> None:
        if error is not None:
            raise RuntimeError(
                f"Kafka delivery failed: {error}"
            )

