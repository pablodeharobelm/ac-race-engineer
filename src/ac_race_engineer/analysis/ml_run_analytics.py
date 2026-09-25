from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from ac_race_engineer.domain.ml_analytics import (
    MLRunAnalyticsReport,
)
from ac_race_engineer.repositories.ml_run_repository import (
    MLRunRepository,
)


class MLRunAnalytics:

    def __init__(
        self,
        repository: MLRunRepository | None = None,
    ):
        self.repository = (
            repository
            or MLRunRepository()
        )

    def dataframe(
        self,
    ) -> pd.DataFrame:

        runs = self.repository.list_all()

        if not runs:
            raise ValueError(
                "No ML runs available"
            )

        rows = []

        for run in runs:

            rows.append(
                {
                    "run_id": run.run_id,
                    "created_at": run.created_at,
                    "model_name": run.model_name,
                    "model_id": run.model_id,
                    "dataset_file": run.dataset_file,
                    "target": run.target,
                    "train_rows": run.train_rows,
                    "test_rows": run.test_rows,
                    "train_seed_count": len(
                        run.train_seeds
                    ),
                    "test_seed_count": len(
                        run.test_seeds
                    ),
                    "mae": run.metrics.mae,
                    "rmse": run.metrics.rmse,
                    "r2": run.metrics.r2,
                }
            )

        dataframe = pd.DataFrame(
            rows
        )

        dataframe = (
            dataframe
            .sort_values(
                "created_at"
            )
            .reset_index(
                drop=True
            )
        )

        return dataframe

    def analyze(
        self,
    ) -> MLRunAnalyticsReport:

        dataframe = self.dataframe()

        return MLRunAnalyticsReport(
            run_count=len(
                dataframe
            ),
            model_names=sorted(
                dataframe[
                    "model_name"
                ].unique().tolist()
            ),
            average_mae=float(
                dataframe[
                    "mae"
                ].mean()
            ),
            average_rmse=float(
                dataframe[
                    "rmse"
                ].mean()
            ),
            average_r2=float(
                dataframe[
                    "r2"
                ].mean()
            ),
            minimum_mae=float(
                dataframe[
                    "mae"
                ].min()
            ),
            maximum_r2=float(
                dataframe[
                    "r2"
                ].max()
            ),
            dataset_file_count=(
                dataframe[
                    "dataset_file"
                ].nunique()
            ),
        )

    def save_csv(
        self,
        output_file: str | Path,
    ) -> Path:

        dataframe = self.dataframe()

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dataframe.to_csv(
            output_file,
            index=False,
        )

        return output_file

    def plot_metrics(
        self,
        output_file: str | Path,
    ) -> Path:

        dataframe = self.dataframe()

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure, axis = plt.subplots()

        run_index = range(
            1,
            len(dataframe) + 1,
        )

        axis.plot(
            run_index,
            dataframe["mae"],
            marker="o",
            label="MAE",
        )

        axis.plot(
            run_index,
            dataframe["rmse"],
            marker="o",
            label="RMSE",
        )

        axis.set_xlabel(
            "ML run"
        )

        axis.set_ylabel(
            "Error"
        )

        axis.set_title(
            "ML error evolution"
        )

        axis.legend()

        axis.grid(
            True,
            alpha=0.3,
        )

        figure.tight_layout()

        figure.savefig(
            output_file,
            dpi=150,
        )

        plt.close(
            figure
        )

        return output_file

    def plot_r2(
        self,
        output_file: str | Path,
    ) -> Path:

        dataframe = self.dataframe()

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure, axis = plt.subplots()

        run_index = range(
            1,
            len(dataframe) + 1,
        )

        axis.plot(
            run_index,
            dataframe["r2"],
            marker="o",
        )

        axis.set_xlabel(
            "ML run"
        )

        axis.set_ylabel(
            "R2"
        )

        axis.set_title(
            "R2 evolution"
        )

        axis.grid(
            True,
            alpha=0.3,
        )

        figure.tight_layout()

        figure.savefig(
            output_file,
            dpi=150,
        )

        plt.close(
            figure
        )

        return output_file

