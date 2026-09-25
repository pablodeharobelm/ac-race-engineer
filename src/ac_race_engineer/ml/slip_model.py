import uuid
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.model_selection import (
    GroupShuffleSplit,
)

from ac_race_engineer.domain.ml import (
    MLTrainingResult,
)

FEATURE_COLUMNS = (
    "absolute_parameter_delta_from_baseline",
)

TARGET_COLUMN = (
    "front_slip_angle_deg"
)


class FrontSlipModelTrainer:

    def __init__(
        self,
        output_directory: str | Path = "data/models/front_slip",
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def train(
        self,
        dataset_file: str | Path,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> MLTrainingResult:

        if not 0 < test_size < 1:
            raise ValueError(
                "test_size must be between 0 and 1"
            )

        dataframe = self._load_dataset(
            dataset_file
        )

        seeds = dataframe[
            "seed"
        ].unique()

        if len(seeds) < 2:
            raise ValueError(
                "At least two seeds are required "
                "for grouped train/test splitting"
            )

        splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=test_size,
            random_state=random_state,
        )

        train_index, test_index = next(
            splitter.split(
                dataframe,
                groups=dataframe["seed"],
            )
        )

        train_data = (
            dataframe.iloc[
                train_index
            ]
        )

        test_data = (
            dataframe.iloc[
                test_index
            ]
        )

        x_train = train_data[
            list(FEATURE_COLUMNS)
        ]

        y_train = train_data[
            TARGET_COLUMN
        ]

        x_test = test_data[
            list(FEATURE_COLUMNS)
        ]

        y_test = test_data[
            TARGET_COLUMN
        ]

        model = LinearRegression()

        model.fit(
            x_train,
            y_train,
        )

        predictions = model.predict(
            x_test
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

        model_id = str(
            uuid.uuid4()
        )

        model_file = (
            self.output_directory
            / f"{model_id}.joblib"
        )

        report_file = (
            self.output_directory
            / f"{model_id}.json"
        )

        bundle = {
            "model": model,
            "features": list(
                FEATURE_COLUMNS
            ),
            "target": TARGET_COLUMN,
            "sklearn_version": (
                sklearn.__version__
            ),
        }

        joblib.dump(
            bundle,
            model_file,
        )

        train_seeds = sorted(
            int(seed)
            for seed in train_data[
                "seed"
            ].unique()
        )

        test_seeds = sorted(
            int(seed)
            for seed in test_data[
                "seed"
            ].unique()
        )

        result = MLTrainingResult(
            model_id=model_id,
            created_at=datetime.now(UTC),
            target=TARGET_COLUMN,
            features=list(
                FEATURE_COLUMNS
            ),
            train_rows=len(
                train_data
            ),
            test_rows=len(
                test_data
            ),
            train_seeds=train_seeds,
            test_seeds=test_seeds,
            mae=mae,
            rmse=rmse,
            r2=r2,
            coefficient=float(
                model.coef_[0]
            ),
            intercept=float(
                model.intercept_
            ),
            model_file=str(
                model_file
            ),
            report_file=str(
                report_file
            ),
        )

        report_file.write_text(
            result.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        return result

    @staticmethod
    def _load_dataset(
        dataset_file: str | Path,
    ) -> pd.DataFrame:

        dataset_file = Path(
            dataset_file
        )

        if not dataset_file.exists():
            raise FileNotFoundError(
                f"ML dataset not found: "
                f"{dataset_file}"
            )

        if (
            dataset_file.suffix
            == ".parquet"
        ):
            dataframe = pd.read_parquet(
                dataset_file
            )

        elif (
            dataset_file.suffix
            == ".csv"
        ):
            dataframe = pd.read_csv(
                dataset_file
            )

        else:
            raise ValueError(
                "Dataset must be CSV or Parquet"
            )

        required_columns = {
            "seed",
            TARGET_COLUMN,
            *FEATURE_COLUMNS,
        }

        missing_columns = (
            required_columns
            - set(dataframe.columns)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(
                    missing_columns
                )
            )

            raise ValueError(
                f"Missing ML columns: "
                f"{missing}"
            )

        dataframe = dataframe[
            [
                "seed",
                *FEATURE_COLUMNS,
                TARGET_COLUMN,
            ]
        ].dropna()

        if dataframe.empty:
            raise ValueError(
                "ML dataset is empty"
            )

        return dataframe

