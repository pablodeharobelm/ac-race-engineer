from ac_race_engineer.domain.car import (
    CarDefinition,
    Drivetrain,
    EngineLayout,
    SetupParameterDefinition,
)
from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.repositories.car_repository import (
    CarRepository,
)
from ac_race_engineer.repositories.setup_repository import (
    SetupRepository,
)


def create_test_car() -> CarDefinition:

    return CarDefinition(
        car_id="test_car",
        manufacturer="Test",
        model="Race Car",
        drivetrain=Drivetrain.RWD,
        engine_layout=EngineLayout.FRONT,
        mass_kg=1000,
        max_rpm=7500,
        fuel_capacity_l=45,
        setup_parameters={
            "front_pressure": (
                SetupParameterDefinition(
                    key="front_pressure",
                    display_name=(
                        "Front pressure"
                    ),
                    unit="psi",
                    minimum=20,
                    maximum=30,
                    step=0.1,
                )
            )
        },
    )


def test_car_repository_save_and_load(
    tmp_path,
):

    repository = CarRepository(
        directory=tmp_path / "cars"
    )

    car = create_test_car()

    repository.save(
        car
    )

    loaded = repository.get(
        "test_car"
    )

    assert loaded.car_id == car.car_id
    assert loaded.mass_kg == 1000


def test_car_repository_lists_cars(
    tmp_path,
):

    repository = CarRepository(
        directory=tmp_path / "cars"
    )

    repository.save(
        create_test_car()
    )

    cars = repository.list_all()

    assert len(cars) == 1

    assert (
        cars[0].car_id
        == "test_car"
    )


def test_setup_repository_save_and_load(
    tmp_path,
):

    repository = SetupRepository(
        directory=tmp_path / "setups"
    )

    setup = CarSetup(
        car_id="test_car",
        name="Baseline",
        values={
            "front_pressure": 24.5
        },
    )

    repository.save(
        setup
    )

    loaded = repository.get(
        car_id="test_car",
        setup_id=setup.setup_id,
    )

    assert (
        loaded.setup_id
        == setup.setup_id
    )

    assert (
        loaded.values[
            "front_pressure"
        ]
        == 24.5
    )


def test_setup_repository_lists_car_setups(
    tmp_path,
):

    repository = SetupRepository(
        directory=tmp_path / "setups"
    )

    setup_a = CarSetup(
        car_id="test_car",
        name="Setup A",
        values={},
    )

    setup_b = CarSetup(
        car_id="test_car",
        name="Setup B",
        values={},
    )

    repository.save(
        setup_a
    )

    repository.save(
        setup_b
    )

    setups = repository.list_for_car(
        "test_car"
    )

    assert len(setups) == 2