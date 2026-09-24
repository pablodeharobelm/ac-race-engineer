import os

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://"
    "ac_race:ac_race_dev"
    "@localhost:5432/"
    "ac_race_engineer"
)


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        DEFAULT_DATABASE_URL,
    )