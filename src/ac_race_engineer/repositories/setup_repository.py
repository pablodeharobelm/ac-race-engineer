from pathlib import Path

from ac_race_engineer.domain.setup import (
    CarSetup,
)


class SetupRepository:

    def __init__(
        self,
        directory: str | Path = "data/setups",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        setup: CarSetup,
    ) -> Path:

        car_directory = (
            self.directory
            / setup.car_id
        )

        car_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            car_directory
            / f"{setup.setup_id}.json"
        )

        file_path.write_text(
            setup.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return file_path

    def get(
        self,
        car_id: str,
        setup_id: str,
    ) -> CarSetup:

        file_path = (
            self.directory
            / car_id
            / f"{setup_id}.json"
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Setup not found: {setup_id}"
            )

        return CarSetup.model_validate_json(
            file_path.read_text(
                encoding="utf-8"
            )
        )

    def list_for_car(
        self,
        car_id: str,
    ) -> list[CarSetup]:

        car_directory = (
            self.directory
            / car_id
        )

        if not car_directory.exists():
            return []

        setups = []

        for file_path in sorted(
            car_directory.glob(
                "*.json"
            )
        ):
            setups.append(
                CarSetup.model_validate_json(
                    file_path.read_text(
                        encoding="utf-8"
                    )
                )
            )

        return setups

