import pytest

from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.services.experiment_runner import (
    ExperimentRunner,
)


def create_setups():
    baseline = CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={
            "front_pressure": 24.5,
            "rear_pressure": 24.5,
        },
    )

    candidate = CarSetup(
        car_id="mazda_mx5_cup",
        name="Higher front pressure",
        values={
            "front_pressure": 25.0,
            "rear_pressure": 24.5,
        },
    )

    return baseline, candidate


def test_experiment_runner_runs_complete_experiment(
    tmp_path,
):
    baseline, candidate = create_setups()

    runner = ExperimentRunner(
        output_directory=(
            tmp_path
            / "experiments"
        ),
        session_directory=(
            tmp_path
            / "sessions"
        ),
    )

    result = runner.run(
        baseline_setup=baseline,
        candidate_setup=candidate,
        seed=42,
        hz=20,
        sample_count=200,
    )

    assert result.experiment_id

    assert (
        result.baseline_setup_id
        == baseline.setup_id
    )

    assert (
        result.candidate_setup_id
        == candidate.setup_id
    )

    assert (
        result.comparison.car_id
        == "mazda_mx5_cup"
    )

    front_pressure_delta = (
        result
        .comparison
        .tyres["FL"]
        .pressure_psi
        .delta
    )

    assert front_pressure_delta > 0

    result_file = (
        tmp_path
        / "experiments"
        / f"{result.experiment_id}.json"
    )

    assert result_file.exists()


def test_experiment_runner_is_reproducible(
    tmp_path,
):
    baseline, candidate = create_setups()

    runner = ExperimentRunner(
        output_directory=(
            tmp_path
            / "experiments"
        ),
        session_directory=(
            tmp_path
            / "sessions"
        ),
    )

    result_a = runner.run(
        baseline_setup=baseline,
        candidate_setup=candidate,
        seed=42,
        sample_count=200,
    )

    result_b = runner.run(
        baseline_setup=baseline,
        candidate_setup=candidate,
        seed=42,
        sample_count=200,
    )

    delta_a = (
        result_a
        .comparison
        .tyres["FL"]
        .pressure_psi
        .delta
    )

    delta_b = (
        result_b
        .comparison
        .tyres["FL"]
        .pressure_psi
        .delta
    )

    assert delta_a == pytest.approx(
        delta_b
    )


def test_experiment_runner_rejects_different_cars(
    tmp_path,
):
    baseline = CarSetup(
        car_id="mazda_mx5_cup",
        name="Baseline",
        values={},
    )

    candidate = CarSetup(
        car_id="other_car",
        name="Invalid candidate",
        values={},
    )

    runner = ExperimentRunner(
        output_directory=(
            tmp_path
            / "experiments"
        ),
        session_directory=(
            tmp_path
            / "sessions"
        ),
    )

    with pytest.raises(
        ValueError,
        match="same car",
    ):
        runner.run(
            baseline_setup=baseline,
            candidate_setup=candidate,
        )