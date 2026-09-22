from datetime import UTC, datetime

import pytest

from ac_race_engineer.domain.ml_tracking import (
    MLRunMetrics,
    MLRunRecord,
)
from ac_race_engineer.repositories.ml_run_repository import (
    MLRunRepository,
)


def create_run(
    run_id: str,
) -> MLRunRecord:

    return MLRunRecord(
        run_id=run_id,
        created_at=datetime.now(UTC),
        model_name="linear_regression",
        model_id="model-123",
        dataset_file="dataset.parquet",
        model_file="model.joblib",
        report_file="report.json",
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
        metrics=MLRunMetrics(
            mae=0.01,
            rmse=0.02,
            r2=0.98,
        ),
        parameters={
            "test_size": 0.2,
        },
        library_versions={
            "python": "3.13",
            "scikit-learn": "1.9",
        },
    )


def test_ml_run_repository_save_and_list(
    tmp_path,
):
    repository = MLRunRepository(
        tmp_path / "runs.jsonl"
    )

    repository.save(
        create_run("run-1")
    )

    repository.save(
        create_run("run-2")
    )

    runs = repository.list_all()

    assert len(runs) == 2

    assert runs[0].run_id == "run-1"
    assert runs[1].run_id == "run-2"


def test_ml_run_repository_get(
    tmp_path,
):
    repository = MLRunRepository(
        tmp_path / "runs.jsonl"
    )

    repository.save(
        create_run("run-123")
    )

    run = repository.get(
        "run-123"
    )

    assert run.model_name == "linear_regression"

    assert run.metrics.r2 == pytest.approx(
        0.98
    )


def test_ml_run_repository_rejects_unknown_run(
    tmp_path,
):
    repository = MLRunRepository(
        tmp_path / "runs.jsonl"
    )

    with pytest.raises(
        FileNotFoundError,
        match="ML run not found",
    ):
        repository.get(
            "unknown"
        )