from pathlib import Path

import pandas as pd
import pytest

from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.services.ml_dataset_builder import (
    MLDatasetBuilder,
)


def create_baseline():
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


def create_builder(
    tmp_path,
):
    return MLDatasetBuilder(
        output_directory=(
            tmp_path / "ml"
        ),
        sweep_directory=(
            tmp_path / "sweeps"
        ),
        experiment_directory=(
            tmp_path / "experiments"
        ),
        session_directory=(
            tmp_path / "sessions"
        ),
    )


def test_ml_dataset_generates_expected_rows(
    tmp_path,
):
    builder = create_builder(
        tmp_path
    )

    result = builder.build(
        baseline_setup=create_baseline(),
        parameter="front_pressure",
        values=[
            24.0,
            24.5,
            25.0,
        ],
        seeds=[
            10,
            20,
        ],
        sample_count=100,
    )

    assert result.row_count == 6
    assert result.sweep_count == 2

    dataframe = pd.read_csv(
        result.csv_file
    )

    assert len(dataframe) == 6

    assert set(
        dataframe["seed"]
    ) == {
        10,
        20,
    }


def test_ml_dataset_contains_engineered_features(
    tmp_path,
):
    builder = create_builder(
        tmp_path
    )

    result = builder.build(
        baseline_setup=create_baseline(),
        parameter="front_pressure",
        values=[
            24.0,
            25.0,
        ],
        seeds=[
            42,
        ],
        sample_count=100,
    )

    dataframe = pd.read_csv(
        result.csv_file
    )

    assert (
        "absolute_parameter_delta_from_baseline"
        in dataframe.columns
    )

    assert (
        "front_rear_pressure_delta"
        in dataframe.columns
    )

    assert (
        "front_rear_slip_delta"
        in dataframe.columns
    )


def test_ml_dataset_creates_csv_and_parquet(
    tmp_path,
):
    builder = create_builder(
        tmp_path
    )

    result = builder.build(
        baseline_setup=create_baseline(),
        parameter="front_pressure",
        values=[
            24.0,
            25.0,
        ],
        seeds=[
            42,
        ],
        sample_count=100,
    )

    assert Path(
        result.csv_file
    ).exists()

    assert Path(
        result.parquet_file
    ).exists()

    parquet = pd.read_parquet(
        result.parquet_file
    )

    assert len(parquet) == 2


def test_ml_dataset_rejects_empty_seeds(
    tmp_path,
):
    builder = create_builder(
        tmp_path
    )

    with pytest.raises(
        ValueError,
        match="seed",
    ):
        builder.build(
            baseline_setup=create_baseline(),
            parameter="front_pressure",
            values=[
                24.0,
                25.0,
            ],
            seeds=[],
            sample_count=100,
        )