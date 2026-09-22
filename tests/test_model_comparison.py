import pandas as pd

from ac_race_engineer.ml.model_comparison import (
    FrontSlipModelComparison,
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

            delta = (
                pressure
                - 24.5
            )

            absolute_delta = abs(
                delta
            )

            slip = (
                2.7
                + absolute_delta
                * 0.08
                + delta
                * 0.01
                + seed
                * 0.00001
            )

            rows.append(
                {
                    "seed": seed,
                    "parameter_delta_from_baseline": (
                        delta
                    ),
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


def test_model_comparison_runs_all_models(
    tmp_path,
):
    dataset = create_dataset(
        tmp_path
    )

    comparison = (
        FrontSlipModelComparison(
            output_directory=(
                tmp_path / "comparison"
            )
        )
    )

    result = comparison.compare(
        dataset
    )

    names = {
        model.model_name
        for model in result.models
    }

    assert names == {
        "linear_regression",
        "polynomial_regression",
        "random_forest",
    }


def test_model_comparison_uses_grouped_split(
    tmp_path,
):
    dataset = create_dataset(
        tmp_path
    )

    comparison = (
        FrontSlipModelComparison(
            output_directory=(
                tmp_path / "comparison"
            )
        )
    )

    result = comparison.compare(
        dataset
    )

    assert (
        set(result.train_seeds)
        .isdisjoint(
            result.test_seeds
        )
    )


def test_model_comparison_metrics_are_valid(
    tmp_path,
):
    dataset = create_dataset(
        tmp_path
    )

    comparison = (
        FrontSlipModelComparison(
            output_directory=(
                tmp_path / "comparison"
            )
        )
    )

    result = comparison.compare(
        dataset
    )

    for model in result.models:

        assert model.mae >= 0
        assert model.rmse >= 0

        assert model.r2 > 0.8


def test_model_comparison_creates_report(
    tmp_path,
):
    dataset = create_dataset(
        tmp_path
    )

    comparison = (
        FrontSlipModelComparison(
            output_directory=(
                tmp_path / "comparison"
            )
        )
    )

    result = comparison.compare(
        dataset
    )

    from pathlib import Path

    assert Path(
        result.report_file
    ).exists()