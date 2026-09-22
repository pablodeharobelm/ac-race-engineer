from pathlib import Path

from ac_race_engineer.ml.model_comparison import (
    FrontSlipModelComparison,
)


def main():

    dataset_directory = Path(
        "data/ml"
    )

    datasets = list(
        dataset_directory.glob(
            "*.parquet"
        )
    )

    if not datasets:
        raise FileNotFoundError(
            "No ML datasets found."
        )

    latest_dataset = max(
        datasets,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    comparison = (
        FrontSlipModelComparison()
    )

    result = comparison.compare(
        latest_dataset
    )

    print()
    print("MODEL COMPARISON")
    print("================")
    print()

    print(
        f"Dataset: "
        f"{latest_dataset}"
    )

    print(
        f"Train seeds: "
        f"{result.train_seeds}"
    )

    print(
        f"Test seeds: "
        f"{result.test_seeds}"
    )

    print()

    print(
        f"{'MODEL':25}"
        f"{'MAE':>12}"
        f"{'RMSE':>12}"
        f"{'R2':>12}"
    )

    print(
        "-" * 61
    )

    for model in result.models:

        print(
            f"{model.model_name:25}"
            f"{model.mae:12.6f}"
            f"{model.rmse:12.6f}"
            f"{model.r2:12.6f}"
        )

    print()

    print(
        f"Report: "
        f"{result.report_file}"
    )


if __name__ == "__main__":
    main()