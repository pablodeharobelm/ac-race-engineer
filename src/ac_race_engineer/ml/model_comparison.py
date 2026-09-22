import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sklearn.ensemble import (
    RandomForestRegressor,
)
from sklearn.linear_model import (
    LinearRegression,
)
from sklearn.metrics import (
    mean_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.model_selection import (
    GroupShuffleSplit,
)
from sklearn.pipeline import (
    Pipeline,
)
from sklearn.preprocessing import (
    PolynomialFeatures,
)

from ac_race_engineer.domain.ml import (
    MLModelComparisonResult,
    MLModelMetrics,
)

FEATURE_COLUMNS = (
    "parameter_delta_from_baseline",
    "absolute_parameter_delta_from_baseline",
)

TARGET_COLUMN = (
    "front_slip_angle_deg"
)


class FrontSlipModelComparison:

    def __init__(
        self,
        output_directory: str | Path = (
            "data/analysis/model_comparison"
        ),
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def compare(
        self,
        dataset_file: str | Path,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> MLModelComparisonResult:

        dataframe = self._load_dataset(
            dataset_file
        )

        if not 0 < test_size < 1:
            raise ValueError(
                "test_size must be between 0 and 1"
            )

        if (
            dataframe["seed"].nunique()
            < 2
        ):
            raise ValueError(
                "At least two seeds are required"
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

        train_data = dataframe.iloc[
            train_index
        ]

        test_data = dataframe.iloc[
            test_index
        ]

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

        models = {
            "linear_regression": (
                LinearRegression()
            ),
            "polynomial_regression": (
                Pipeline(
                    steps=[
                        (
                            "polynomial",
                            PolynomialFeatures(
                                degree=2,
                                include_bias=False,
                            ),
                        ),
                        (
                            "model",
                            LinearRegression(),
                        ),
                    ]
                )
            ),
            "random_forest": (
                RandomForestRegressor(
                    n_estimators=200,
                    random_state=random_state,
                    n_jobs=-1,
                )
            ),
        }

        metrics = []

        for (
            model_name,
            model,
        ) in models.items():

            model.fit(
                x_train,
                y_train,
            )

            predictions = model.predict(
                x_test
            )

            metrics.append(
                MLModelMetrics(
                    model_name=model_name,
                    mae=float(
                        mean_absolute_error(
                            y_test,
                            predictions,
                        )
                    ),
                    rmse=float(
                        root_mean_squared_error(
                            y_test,
                            predictions,
                        )
                    ),
                    r2=float(
                        r2_score(
                            y_test,
                            predictions,
                        )
                    ),
                )
            )

        comparison_id = str(
            uuid.uuid4()
        )

        report_file = (
            self.output_directory
            / f"{comparison_id}.json"
        )

        result = MLModelComparisonResult(
            comparison_id=comparison_id,
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
            train_seeds=sorted(
                int(seed)
                for seed in train_data[
                    "seed"
                ].unique()
            ),
            test_seeds=sorted(
                int(seed)
                for seed in test_data[
                    "seed"
                ].unique()
            ),
            models=metrics,
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
                f"Dataset not found: "
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

        missing = (
            required_columns
            - set(dataframe.columns)
        )

        if missing:
            raise ValueError(
                "Missing model comparison columns: "
                + ", ".join(
                    sorted(missing)
                )
            )

        return dataframe[
            [
                "seed",
                *FEATURE_COLUMNS,
                TARGET_COLUMN,
            ]
        ].dropna()