from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ac_race_engineer.database.config import get_database_url


def create_database_engine(
    database_url: str | None = None,
    *,
    echo: bool = False,
) -> Engine:
    url = (
        database_url
        if database_url is not None
        else get_database_url()
    )

    return create_engine(
        url,
        echo=echo,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def database_session(
    engine: Engine,
) -> Iterator[Session]:
    session_factory = create_session_factory(engine)
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

