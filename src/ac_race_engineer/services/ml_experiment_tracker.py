import platform
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import sklearn

from ac_race_engineer.domain.ml import (
    MLTrainingResult,
)
from ac_race_engineer.domain.ml_tracking import (
    MLRunMetrics,
    MLRunRecord,
)
from ac_race_engineer.repositories.ml_run_repository import (
    MLRunRepository,
)


class MLExperimentTracker:

    def __init__(
        self,
        repository: MLRunRepository | None = None,
    ):
        self.repository = (
            repository
            or MLRunRepository()
        )

    def log_training(
        self,
        training: MLTrainingResult,
        dataset_file: str | Path,
        model_name: str,
        parameters: dict[
            str,
            str | int | float | bool,
        ]
        | None = None,
    ) -> MLRunRecord:

        run = MLRunRecord(
            run_id=str(
                uuid.uuid4()
            ),
            created_at=datetime.now(UTC),
            model_name=model_name,
            model_id=training.model_id,
            dataset_file=str(
                dataset_file
            ),
            model_file=training.model_file,
            report_file=training.report_file,
            target=training.target,
            features=training.features,
            train_rows=training.train_rows,
            test_rows=training.test_rows,
            train_seeds=(
                training.train_seeds
            ),
            test_seeds=(
                training.test_seeds
            ),
            metrics=MLRunMetrics(
                mae=training.mae,
                rmse=training.rmse,
                r2=training.r2,
            ),
            parameters=parameters or {},
            library_versions={
                "python": (
                    platform.python_version()
                ),
                "pandas": pd.__version__,
                "scikit-learn": (
                    sklearn.__version__
                ),
            },
        )

        self.repository.save(
            run
        )

        return run

