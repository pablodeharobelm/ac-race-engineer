from pathlib import Path

import pandas as pd

from ac_race_engineer.ml.evaluator import (
    FrontSlipModelEvaluator,
)
from ac_race_engineer.ml.slip_model import (
    FrontSlipModelTrainer,
)


def create_dataset(
    tmp_path,
):
    rows = []

    for seed in [
        10,
        20,
        30,
        40,
        50,
    ]:

        for pressure in [
            23.0,
            23.5,
            24.0,
            24.5,
            25.0,
            25.5,
            26.0,
        ]:

            distance = abs(
                pressure
                - 24.5
            )

            rows.append(
                {
                    "seed": seed,
                    "absolute_parameter_delta_from_baseline": (
                        distance
                    ),
                    "front_slip_angle_deg": (
                        2.7
                        + distance * 0.08
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


def test_model_evaluator_creates_metrics_and_plots(
    tmp_path,
):
    dataset = create_dataset(
        tmp_path
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    training = trainer.train(
        dataset
    )

    evaluator = FrontSlipModelEvaluator(
        model_file=training.model_file,
        output_directory=(
            tmp_path / "plots"
        ),
    )

    result = evaluator.evaluate(
        dataset
    )

    assert result.test_rows > 0
    assert result.r2 > 0.95

    assert Path(
        result.actual_vs_predicted_plot
    ).exists()

    assert Path(
        result.residual_plot
    ).exists()