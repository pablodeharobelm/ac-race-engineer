from sqlalchemy import text

from ac_race_engineer.database.config import (
    DEFAULT_DATABASE_URL,
    get_database_url,
)
from ac_race_engineer.database.health import (
    check_database_connection,
)
from ac_race_engineer.database.session import (
    create_database_engine,
    create_session_factory,
)


def test_default_database_url(
    monkeypatch,
):

    monkeypatch.delenv(
        "DATABASE_URL",
        raising=False,
    )

    assert (
        get_database_url()
        == DEFAULT_DATABASE_URL
    )


def test_database_url_from_environment(
    monkeypatch,
):

    expected = "sqlite+pysqlite:///:memory:"

    monkeypatch.setenv(
        "DATABASE_URL",
        expected,
    )

    assert (
        get_database_url()
        == expected
    )


def test_database_health_check():

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    try:
        assert check_database_connection(
            engine
        )

    finally:
        engine.dispose()


def test_session_factory():

    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:"
    )

    try:
        session_factory = (
            create_session_factory(
                engine
            )
        )

        with session_factory() as session:

            value = session.execute(
                text(
                    "SELECT 42"
                )
            ).scalar_one()

        assert value == 42

    finally:
        engine.dispose()