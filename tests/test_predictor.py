import pandas as pd
import pytest

from ac_race_engineer.ml.predictor import (
    FrontSlipPredictor,
)
from ac_race_engineer.ml.slip_model import (
    FrontSlipModelTrainer,
)


def create_model(
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

    dataset_file = (
        tmp_path
        / "dataset.parquet"
    )

    dataframe.to_parquet(
        dataset_file,
        index=False,
    )

    trainer = FrontSlipModelTrainer(
        output_directory=(
            tmp_path / "models"
        )
    )

    result = trainer.train(
        dataset_file
    )

    return result.model_file


def test_predictor_loads_model_and_predicts(
    tmp_path,
):
    model_file = create_model(
        tmp_path
    )

    predictor = FrontSlipPredictor(
        model_file
    )

    result = predictor.predict_pressure(
        pressure_psi=25.5,
        baseline_pressure_psi=24.5,
    )

    assert (
        result.target
        == "front_slip_angle_deg"
    )

    assert result.prediction == pytest.approx(
        2.78,
        abs=0.01,
    )


def test_predictor_baseline_has_lower_slip(
    tmp_path,
):
    model_file = create_model(
        tmp_path
    )

    predictor = FrontSlipPredictor(
        model_file
    )

    baseline = predictor.predict_pressure(
        24.5
    )

    far_from_baseline = (
        predictor.predict_pressure(
            26.0
        )
    )

    assert (
        far_from_baseline.prediction
        > baseline.prediction
    )


def test_predictor_rejects_missing_feature(
    tmp_path,
):
    model_file = create_model(
        tmp_path
    )

    predictor = FrontSlipPredictor(
        model_file
    )

    with pytest.raises(
        ValueError,
        match="Missing prediction features",
    ):
        predictor.predict(
            {}
        )