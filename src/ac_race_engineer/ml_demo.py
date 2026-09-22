from pathlib import Path

from ac_race_engineer.ml.slip_model import (
    FrontSlipModelTrainer,
)
from ac_race_engineer.services.ml_experiment_tracker import (
    MLExperimentTracker,
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
            "No ML datasets found. "
            "Run ml_dataset_demo first."
        )

    latest_dataset = max(
        datasets,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    trainer = FrontSlipModelTrainer()

    result = trainer.train(
        latest_dataset
    )
    tracker = MLExperimentTracker()

    run = tracker.log_training(
        training=result,
        dataset_file=latest_dataset,
        model_name="linear_regression",
        parameters={
            "test_size": 0.2,
            "random_state": 42,
        },
    )

    print()
    print("FRONT SLIP MODEL")
    print("================")
    print()

    print(
        f"Dataset: "
        f"{latest_dataset}"
    )

    print()

    print(
        f"Train rows: "
        f"{result.train_rows}"
    )

    print(
        f"Test rows: "
        f"{result.test_rows}"
    )

    print()

    print(
        f"Train seeds: "
        f"{result.train_seeds}"
    )

    print(
        f"Test seeds: "
        f"{result.test_seeds}"
    )

    print()

    print("METRICS")
    print("-------")

    print(
        f"MAE:  "
        f"{result.mae:.6f}"
    )

    print(
        f"RMSE: "
        f"{result.rmse:.6f}"
    )

    print(
        f"R2:   "
        f"{result.r2:.6f}"
    )

    print()

    print("MODEL")
    print("-----")

    print(
        f"Intercept: "
        f"{result.intercept:.6f}"
    )

    print(
        "Absolute pressure delta "
        f"coefficient: "
        f"{result.coefficient:.6f}"
    )

    print()

    print(
        f"Model: "
        f"{result.model_file}"
    )

    print(
        f"Report: "
        f"{result.report_file}"
    )

    print()

    print(
        f"Tracked ML run: "
        f"{run.run_id}"
    )


if __name__ == "__main__":
    main()