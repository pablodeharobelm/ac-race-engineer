from pathlib import Path

from ac_race_engineer.domain.car import CarDefinition


class CarRepository:

    def __init__(
        self,
        directory: str | Path = "data/catalog/cars",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        car: CarDefinition,
    ) -> Path:

        file_path = (
            self.directory
            / f"{car.car_id}.json"
        )

        file_path.write_text(
            car.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return file_path

    def get(
        self,
        car_id: str,
    ) -> CarDefinition:

        file_path = (
            self.directory
            / f"{car_id}.json"
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Car not found: {car_id}"
            )

        return CarDefinition.model_validate_json(
            file_path.read_text(
                encoding="utf-8"
            )
        )

    def exists(
        self,
        car_id: str,
    ) -> bool:

        return (
            self.directory
            / f"{car_id}.json"
        ).exists()

    def list_all(
        self,
    ) -> list[CarDefinition]:

        cars = []

        for file_path in sorted(
            self.directory.glob(
                "*.json"
            )
        ):
            cars.append(
                CarDefinition.model_validate_json(
                    file_path.read_text(
                        encoding="utf-8"
                    )
                )
            )

        return cars

