"""Optional confluent-kafka clients. Importing the core project does not require Kafka."""

import re
import time
from collections.abc import Iterator
from uuid import uuid4

from ac_race_engineer.domain.session import SessionType
from ac_race_engineer.kafka.messages import KafkaTelemetryMessage
from ac_race_engineer.telemetry.models import TelemetryFrame


def validate_topic(topic: str) -> None:
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,249}", topic) or topic in {".", ".."}:
        raise ValueError("Invalid Kafka topic name")


def kafka_library():
    try:
        import confluent_kafka
    except ImportError as exc:
        raise RuntimeError('Kafka support requires: python -m pip install ".[kafka]"') from exc
    return confluent_kafka


class KafkaTelemetryProducer:
    def __init__(
        self,
        bootstrap_servers: str = "127.0.0.1:9092",
        topic: str = "telemetry.raw",
        *,
        source: str = "simulator",
        session_type: SessionType = SessionType.TEST,
        setup_id: str | None = None,
        client=None,
    ):
        validate_topic(topic)
        if not bootstrap_servers.strip():
            raise ValueError("bootstrap_servers cannot be empty")
        self.topic = topic
        self.source = source
        self.session_type = session_type
        self.setup_id = setup_id
        self.client = (
            client
            if client is not None
            else kafka_library().Producer(
                {
                    "bootstrap.servers": bootstrap_servers,
                    "client.id": "ac-race-engineer",
                    "enable.idempotence": True,
                    "acks": "all",
                    "delivery.timeout.ms": 30000,
                }
            )
        )
        self.delivered_count = 0
        self._errors = []

    def _delivered(self, error, message) -> None:
        if error is not None:
            self._errors.append(str(error))
        else:
            self.delivered_count += 1

    def send(self, frame: TelemetryFrame) -> None:
        message = KafkaTelemetryMessage(
            source=self.source, session_type=self.session_type, setup_id=self.setup_id, frame=frame
        )
        self.client.produce(
            self.topic, key=message.key, value=message.encode(), on_delivery=self._delivered
        )
        self.client.poll(0)

    def flush(self, timeout_seconds: float = 30) -> int:
        """Only return successfully after all queued messages are acknowledged."""
        remaining = self.client.flush(timeout_seconds)
        if remaining:
            raise TimeoutError(f"Kafka has {remaining} undelivered messages")
        if self._errors:
            errors, self._errors = self._errors, []
            raise RuntimeError("Kafka delivery failed: " + "; ".join(errors))
        return self.delivered_count


def create_telemetry_topic(
    bootstrap_servers: str = "127.0.0.1:9092", topic: str = "telemetry.raw", partitions: int = 3
) -> None:
    validate_topic(topic)
    if partitions <= 0:
        raise ValueError("partitions must be positive")
    library = kafka_library()
    from confluent_kafka.admin import AdminClient, NewTopic

    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    future = admin.create_topics(
        [NewTopic(topic, num_partitions=partitions, replication_factor=1)], request_timeout=15
    )[topic]
    try:
        future.result(timeout=20)
    except library.KafkaException as exc:
        if exc.args[0].code() != library.KafkaError.TOPIC_ALREADY_EXISTS:
            raise


def consume_telemetry(
    bootstrap_servers: str = "127.0.0.1:9092",
    topic: str = "telemetry.raw",
    *,
    limit: int = 10,
    timeout_seconds: float = 30,
) -> Iterator[KafkaTelemetryMessage]:
    """Diagnostic consumer; no offset commits and no interference with Spark checkpoints."""
    validate_topic(topic)
    if limit <= 0 or timeout_seconds <= 0:
        raise ValueError("limit and timeout must be positive")
    library = kafka_library()
    consumer = library.Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": f"ac-inspect-{uuid4().hex}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    count = 0
    deadline = time.monotonic() + timeout_seconds
    try:
        consumer.subscribe([topic])
        while count < limit and time.monotonic() < deadline:
            record = consumer.poll(min(1.0, max(0.0, deadline - time.monotonic())))
            if record is None:
                continue
            if record.error():
                raise library.KafkaException(record.error())
            if record.value() is None:
                raise ValueError("Kafka tombstone has no telemetry payload")
            yield KafkaTelemetryMessage.model_validate_json(record.value())
            count += 1
    finally:
        consumer.close()
