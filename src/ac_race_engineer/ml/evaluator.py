from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    root_mean_squared_error,
)

from ac_race_engineer.domain.ml import (
    MLModelEvaluationResult,
    MLTrainingResult,
)
from ac_race_engineer.ml.predictor import (
    FrontSlipPredictor,
)


class FrontSlipModelEvaluator:

    def __init__(
        self,
        model_file: str | Path,
        output_directory: str | Path = (
            "data/analysis/ml"
        ),
    ):
        self.model_file = Path(
            model_file
        )

        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.predictor = (
            FrontSlipPredictor(
                self.model_file
            )
        )

    def evaluate(
        self,
        dataset_file: str | Path,
    ) -> MLModelEvaluationResult:

        dataset_file = Path(
            dataset_file
        )

        training_report = (
            self._load_training_report()
        )

        dataframe = self._load_dataset(
            dataset_file
        )

        test_data = dataframe[
            dataframe["seed"].isin(
                training_report.test_seeds
            )
        ].copy()

        if test_data.empty:
            raise ValueError(
                "Dataset does not contain "
                "the model test seeds"
            )

        x_test = test_data[
            self.predictor.features
        ]

        y_test = test_data[
            self.predictor.target
        ]

        predictions = (
            self.predictor.model.predict(
                x_test
            )
        )

        mae = float(
            mean_absolute_error(
                y_test,
                predictions,
            )
        )

        rmse = float(
            root_mean_squared_error(
                y_test,
                predictions,
            )
        )

        r2 = float(
            r2_score(
                y_test,
                predictions,
            )
        )

        actual_plot = (
            self.output_directory
            / (
                f"{self.model_file.stem}"
                "_actual_vs_predicted.png"
            )
        )

        residual_plot = (
            self.output_directory
            / (
                f"{self.model_file.stem}"
                "_residuals.png"
            )
        )

        self._plot_actual_vs_predicted(
            actual=y_test,
            predicted=predictions,
            output_file=actual_plot,
        )

        self._plot_residuals(
            actual=y_test,
            predicted=predictions,
            output_file=residual_plot,
        )

        return MLModelEvaluationResult(
            model_file=str(
                self.model_file
            ),
            dataset_file=str(
                dataset_file
            ),
            test_rows=len(
                test_data
            ),
            test_seeds=(
                training_report.test_seeds
            ),
            mae=mae,
            rmse=rmse,
            r2=r2,
            actual_vs_predicted_plot=str(
                actual_plot
            ),
            residual_plot=str(
                residual_plot
            ),
        )

    def _load_training_report(
        self,
    ) -> MLTrainingResult:

        report_file = (
            self.model_file.with_suffix(
                ".json"
            )
        )

        if not report_file.exists():
            raise FileNotFoundError(
                "Training report not found: "
                f"{report_file}"
            )

        return MLTrainingResult.model_validate_json(
            report_file.read_text(
                encoding="utf-8"
            )
        )

    @staticmethod
    def _load_dataset(
        dataset_file: Path,
    ) -> pd.DataFrame:

        if not dataset_file.exists():
            raise FileNotFoundError(
                f"Dataset not found: "
                f"{dataset_file}"
            )

        if dataset_file.suffix == ".parquet":
            return pd.read_parquet(
                dataset_file
            )

        if dataset_file.suffix == ".csv":
            return pd.read_csv(
                dataset_file
            )

        raise ValueError(
            "Dataset must be CSV or Parquet"
        )

    @staticmethod
    def _plot_actual_vs_predicted(
        actual,
        predicted,
        output_file: Path,
    ) -> None:

        figure, axis = plt.subplots()

        axis.scatter(
            actual,
            predicted,
        )

        minimum = min(
            actual.min(),
            predicted.min(),
        )

        maximum = max(
            actual.max(),
            predicted.max(),
        )

        axis.plot(
            [
                minimum,
                maximum,
            ],
            [
                minimum,
                maximum,
            ],
        )

        axis.set_xlabel(
            "Actual front slip angle"
        )

        axis.set_ylabel(
            "Predicted front slip angle"
        )

        axis.set_title(
            "Actual vs predicted"
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

    @staticmethod
    def _plot_residuals(
        actual,
        predicted,
        output_file: Path,
    ) -> None:

        residuals = (
            actual.to_numpy()
            - predicted
        )

        figure, axis = plt.subplots()

        axis.scatter(
            predicted,
            residuals,
        )

        axis.axhline(
            0,
        )

        axis.set_xlabel(
            "Predicted front slip angle"
        )

        axis.set_ylabel(
            "Residual"
        )

        axis.set_title(
            "Prediction residuals"
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