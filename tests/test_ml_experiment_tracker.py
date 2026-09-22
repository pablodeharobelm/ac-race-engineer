from datetime import UTC, datetime

from ac_race_engineer.domain.ml import (
    MLTrainingResult,
)
from ac_race_engineer.repositories.ml_run_repository import (
    MLRunRepository,
)
from ac_race_engineer.services.ml_experiment_tracker import (
    MLExperimentTracker,
)


def create_training_result():

    return MLTrainingResult(
        model_id="model-123",
        created_at=datetime.now(UTC),
        target="front_slip_angle_deg",
        features=[
            "absolute_parameter_delta_from_baseline"
        ],
        train_rows=28,
        test_rows=7,
        train_seeds=[
            10,
            20,
            30,
            40,
        ],
        test_seeds=[
            50,
        ],
        mae=0.01,
        rmse=0.02,
        r2=0.98,
        coefficient=0.08,
        intercept=2.7,
        model_file="model.joblib",
        report_file="model.json",
    )


def test_tracker_logs_training(
    tmp_path,
):
    repository = MLRunRepository(
        tmp_path / "runs.jsonl"
    )

    tracker = MLExperimentTracker(
        repository=repository
    )

    training = (
        create_training_result()
    )

    run = tracker.log_training(
        training=training,
        dataset_file="dataset.parquet",
        model_name="linear_regression",
        parameters={
            "test_size": 0.2,
            "random_state": 42,
        },
    )

    assert run.model_id == "model-123"

    assert run.metrics.mae == 0.01

    assert (
        run.parameters[
            "random_state"
        ]
        == 42
    )

    runs = repository.list_all()

    assert len(runs) == 1