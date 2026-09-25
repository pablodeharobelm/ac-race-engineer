from sqlalchemy import Engine, text


def check_database_connection(
    engine: Engine,
) -> bool:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1")
        )

        return result.scalar_one() == 1


def get_database_info(
    engine: Engine,
) -> dict[str, str]:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    current_database(),
                    current_user,
                    version()
                """
            )
        ).one()

    return {
        "database": str(row[0]),
        "user": str(row[1]),
        "version": str(row[2]),
    }

