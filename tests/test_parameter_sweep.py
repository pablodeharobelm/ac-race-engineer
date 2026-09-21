import pytest

from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.services.parameter_sweep import (
    ParameterSweepRunner,
)


def create_baseline_setup():
    return CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={
            "front_pressure": 24.5,
            "rear_pressure": 24.5,
            "front_camber": -2.5,
            "rear_camber": -2.0,
            "brake_bias": 0.64,
        },
    )


def test_parameter_sweep_runs_multiple_values(
    tmp_path,
):
    setup = create_baseline_setup()

    runner = ParameterSweepRunner(
        output_directory=(
            tmp_path / "sweeps"
        ),
        experiment_directory=(
            tmp_path / "experiments"
        ),
        session_directory=(
            tmp_path / "sessions"
        ),
    )

    result = runner.run(
        baseline_setup=setup,
        parameter="front_pressure",
        values=[
            24.0,
            24.5,
            25.0,
        ],
        seed=42,
        sample_count=200,
    )

    assert len(result.points) == 3

    assert (
        result.parameter
        == "front_pressure"
    )

    assert result.baseline_value == 24.5

    assert (
        result.points[0].parameter_value
        == 24.0
    )

    assert (
        result.points[2].parameter_value
        == 25.0
    )


def test_parameter_sweep_pressure_affects_result(
    tmp_path,
):
    setup = create_baseline_setup()

    runner = ParameterSweepRunner(
        output_directory=(
            tmp_path / "sweeps"
        ),
        experiment_directory=(
            tmp_path / "experiments"
        ),
        session_directory=(
            tmp_path / "sessions"
        ),
    )

    result = runner.run(
        baseline_setup=setup,
        parameter="front_pressure",
        values=[
            23.0,
            26.0,
        ],
        seed=42,
        sample_count=300,
    )

    low_pressure = (
        result.points[0]
    )

    high_pressure = (
        result.points[1]
    )

    assert (
        high_pressure.front_pressure_psi
        > low_pressure.front_pressure_psi
    )


def test_parameter_sweep_creates_dataset_files(
    tmp_path,
):
    setup = create_baseline_setup()

    output_directory = (
        tmp_path / "sweeps"
    )

    runner = ParameterSweepRunner(
        output_directory=output_directory,
        experiment_directory=(
            tmp_path / "experiments"
        ),
        session_directory=(
            tmp_path / "sessions"
        ),
    )

    result = runner.run(
        baseline_setup=setup,
        parameter="front_pressure",
        values=[
            24.0,
            25.0,
        ],
        sample_count=100,
    )

    assert (
        output_directory
        / f"{result.sweep_id}.json"
    ).exists()

    assert (
        output_directory
        / f"{result.sweep_id}.csv"
    ).exists()


def test_parameter_sweep_rejects_unknown_parameter(
    tmp_path,
):
    setup = create_baseline_setup()

    runner = ParameterSweepRunner(
        output_directory=(
            tmp_path / "sweeps"
        ),
        experiment_directory=(
            tmp_path / "experiments"
        ),
        session_directory=(
            tmp_path / "sessions"
        ),
    )

    with pytest.raises(
        ValueError,
        match="does not contain parameter",
    ):
        runner.run(
            baseline_setup=setup,
            parameter="rear_wing",
            values=[
                1,
                2,
            ],
        )