import pytest

from ac_race_engineer.domain.car import (
    CarDefinition,
    Drivetrain,
    EngineLayout,
    SetupParameterDefinition,
)
from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.services.setup_service import (
    SetupService,
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
                        "Front tyre pressure"
                    ),
                    unit="psi",
                    minimum=20,
                    maximum=30,
                    step=0.1,
                )
            ),
            "brake_bias": (
                SetupParameterDefinition(
                    key="brake_bias",
                    display_name=(
                        "Brake bias"
                    ),
                    unit="ratio",
                    minimum=0.50,
                    maximum=0.75,
                    step=0.01,
                )
            ),
        },
    )


def test_valid_setup():

    car = create_test_car()

    setup = CarSetup(
        car_id="test_car",
        name="Baseline",
        values={
            "front_pressure": 24.5,
            "brake_bias": 0.64,
        },
    )

    SetupService.validate_setup(
        car=car,
        setup=setup,
    )


def test_setup_rejects_invalid_value():

    car = create_test_car()

    setup = CarSetup(
        car_id="test_car",
        name="Invalid",
        values={
            "front_pressure": 35,
        },
    )

    with pytest.raises(
        ValueError,
        match="outside allowed range",
    ):
        SetupService.validate_setup(
            car=car,
            setup=setup,
        )


def test_setup_rejects_unknown_parameter():

    car = create_test_car()

    setup = CarSetup(
        car_id="test_car",
        name="Invalid",
        values={
            "rocket_boost": 100,
        },
    )

    with pytest.raises(
        ValueError,
        match="Unsupported setup parameter",
    ):
        SetupService.validate_setup(
            car=car,
            setup=setup,
        )


def test_compare_setups():

    setup_a = CarSetup(
        car_id="test_car",
        name="Setup A",
        values={
            "front_pressure": 24.0,
            "brake_bias": 0.64,
        },
    )

    setup_b = CarSetup(
        car_id="test_car",
        name="Setup B",
        values={
            "front_pressure": 24.5,
            "brake_bias": 0.62,
        },
    )

    comparison = SetupService.compare(
        setup_a=setup_a,
        setup_b=setup_b,
    )

    assert len(comparison.changes) == 2

    pressure_change = next(
        change
        for change in comparison.changes
        if change.parameter
        == "front_pressure"
    )

    assert pressure_change.delta == pytest.approx(
        0.5
    )