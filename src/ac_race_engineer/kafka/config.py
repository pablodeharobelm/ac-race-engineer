import os

DEFAULT_BOOTSTRAP_SERVERS = "localhost:9092"
DEFAULT_TELEMETRY_TOPIC = "telemetry.raw"


def get_bootstrap_servers() -> str:
    return os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        DEFAULT_BOOTSTRAP_SERVERS,
    )


def get_telemetry_topic() -> str:
    return os.getenv(
        "KAFKA_TELEMETRY_TOPIC",
        DEFAULT_TELEMETRY_TOPIC,
    )

