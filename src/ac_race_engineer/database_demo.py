from ac_race_engineer.database.health import (
    check_database_connection,
    get_database_info,
)
from ac_race_engineer.database.session import (
    create_database_engine,
)


def main() -> None:
    engine = create_database_engine()

    try:
        healthy = check_database_connection(
            engine
        )

        info = get_database_info(
            engine
        )

        print()
        print("POSTGRESQL CONNECTION")
        print("=====================")
        print(f"Healthy: {healthy}")
        print(
            f"Database: {info['database']}"
        )
        print(
            f"User: {info['user']}"
        )
        print(
            f"Server: {info['version']}"
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

