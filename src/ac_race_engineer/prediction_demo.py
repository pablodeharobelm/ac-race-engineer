from pathlib import Path

from ac_race_engineer.ml.evaluator import (
    FrontSlipModelEvaluator,
)
from ac_race_engineer.ml.predictor import (
    FrontSlipPredictor,
)


def main():

    model_directory = Path(
        "data/models/front_slip"
    )

    model_files = list(
        model_directory.glob(
            "*.joblib"
        )
    )

    if not model_files:
        raise FileNotFoundError(
            "No trained models found. "
            "Run ml_demo first."
        )

    latest_model = max(
        model_files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

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

    predictor = FrontSlipPredictor(
        latest_model
    )

    print()
    print("FRONT SLIP PREDICTIONS")
    print("======================")
    print()

    for pressure in [
        23.0,
        23.5,
        24.0,
        24.5,
        25.0,
        25.3,
        25.5,
        26.0,
    ]:

        result = (
            predictor.predict_pressure(
                pressure
            )
        )

        print(
            f"{pressure:4.1f} PSI"
            f" -> "
            f"{result.prediction:.4f} deg"
        )

    evaluator = (
        FrontSlipModelEvaluator(
            latest_model
        )
    )

    evaluation = evaluator.evaluate(
        latest_dataset
    )

    print()
    print("HELD-OUT EVALUATION")
    print("===================")
    print()

    print(
        f"Test seeds: "
        f"{evaluation.test_seeds}"
    )

    print(
        f"Test rows: "
        f"{evaluation.test_rows}"
    )

    print()

    print(
        f"MAE:  "
        f"{evaluation.mae:.6f}"
    )

    print(
        f"RMSE: "
        f"{evaluation.rmse:.6f}"
    )

    print(
        f"R2:   "
        f"{evaluation.r2:.6f}"
    )

    print()

    print(
        "Actual vs predicted: "
        f"{evaluation.actual_vs_predicted_plot}"
    )

    print(
        "Residuals: "
        f"{evaluation.residual_plot}"
    )


if __name__ == "__main__":
    main()

