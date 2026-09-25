from datetime import UTC, datetime

from ac_race_engineer.kafka.config import (
    get_telemetry_topic,
)
from ac_race_engineer.kafka.producer import (
    KafkaProducer,
)


def main() -> None:
    producer = KafkaProducer()

    producer.publish_json(
        topic=get_telemetry_topic(),
        key="python-demo-001",
        payload={
            "session_id": "python-demo-001",
            "timestamp": datetime.now(UTC),
            "speed_kph": 126.8,
            "rpm": 6820,
            "gear": 4,
            "source": "python-demo",
        },
    )

    remaining = producer.flush()

    if remaining != 0:
        raise RuntimeError(
            f"{remaining} Kafka messages "
            "were not delivered"
        )

    print(
        "Telemetry message published "
        "successfully."
    )


if __name__ == "__main__":
    main()

