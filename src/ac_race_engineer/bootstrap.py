from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.repositories.setup_repository import (
    SetupRepository,
)


def main():

    repository = SetupRepository()

    setup = CarSetup(
        car_id="mazda_mx5_cup",
        name="Development baseline",
        values={
            "front_pressure": 24.5,
            "rear_pressure": 24.5,
            "front_camber": -2.5,
            "rear_camber": -2.0,
            "brake_bias": 0.64,
        },
    )

    output = repository.save(
        setup
    )

    print(
        f"Setup created: {output}"
    )

    print(
        f"Setup ID: {setup.setup_id}"
    )


if __name__ == "__main__":
    main()

