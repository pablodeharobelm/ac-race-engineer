from pathlib import Path

import pandas as pd
import pytest

from ac_race_engineer.ml.slip_model import (
    FrontSlipModelTrainer,
)


def create_ml_dataset(
    tmp_path,
):
    rows = []

    values = [
        23.0,
        23.5,
        24.0,
        24.5,
        25.0,
        25.5,
        26.0,
    ]

    seeds = [
        10,
        20,
        30,
        40,
        50,
    ]

    for seed in seeds:

        for value in values:

            absolute_delta = abs(
                value
                - 24.5
            )

            slip = (
                2.7
                + absolute_delta
                * 0.08
                + seed
                * 0.00001
            )

            rows.append(
                {
                    "seed": seed,
                    "parameter_value": value,
                    "absolute_parameter_delta_from_baseline": (
                        absolute_delta
                    ),
                    "front_slip_angle_deg": (
                        slip
                    ),
                }
            )

    dataframe = pd.DataFrame(
        rows
    )

    file_path = (
        tmp_path
        / "dataset.parquet"
    )

    dataframe.to_parquet(
        file_path,
        index=False,
    )

    return file_path


def test_slip_model_trains(
    tmp_path,
):
    dataset = create_ml_dataset(
        tmp_path
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    result = trainer.train(
        dataset
    )

    assert result.train_rows > 0
    assert result.test_rows > 0

    assert (
        set(result.train_seeds)
        .isdisjoint(
            result.test_seeds
        )
    )


def test_slip_model_has_good_metrics(
    tmp_path,
):
    dataset = create_ml_dataset(
        tmp_path
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    result = trainer.train(
        dataset
    )

    assert result.mae >= 0
    assert result.rmse >= 0

    assert result.r2 > 0.95


def test_slip_model_learns_positive_distance_effect(
    tmp_path,
):
    dataset = create_ml_dataset(
        tmp_path
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    result = trainer.train(
        dataset
    )

    assert result.coefficient > 0

    assert result.coefficient == pytest.approx(
        0.08,
        abs=0.01,
    )


def test_slip_model_saves_artifacts(
    tmp_path,
):
    dataset = create_ml_dataset(
        tmp_path
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    result = trainer.train(
        dataset
    )

    assert Path(
        result.model_file
    ).exists()

    assert Path(
        result.report_file
    ).exists()


def test_slip_model_rejects_single_seed(
    tmp_path,
):
    dataframe = pd.DataFrame(
        {
            "seed": [
                42,
                42,
                42,
            ],
            "absolute_parameter_delta_from_baseline": [
                0.0,
                0.5,
                1.0,
            ],
            "front_slip_angle_deg": [
                2.7,
                2.75,
                2.8,
            ],
        }
    )

    file_path = (
        tmp_path
        / "dataset.csv"
    )

    dataframe.to_csv(
        file_path,
        index=False,
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    with pytest.raises(
        ValueError,
        match="two seeds",
    ):
        trainer.train(
            file_path
        )