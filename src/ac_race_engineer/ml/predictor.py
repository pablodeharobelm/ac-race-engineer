from pathlib import Path

import joblib
import pandas as pd

from ac_race_engineer.domain.ml import (
    MLPredictionResult,
)


class FrontSlipPredictor:

    def __init__(
        self,
        model_file: str | Path,
    ):
        self.model_file = Path(
            model_file
        )

        if not self.model_file.exists():
            raise FileNotFoundError(
                f"Model not found: "
                f"{self.model_file}"
            )

        bundle = joblib.load(
            self.model_file
        )

        self.model = bundle[
            "model"
        ]

        self.features = bundle[
            "features"
        ]

        self.target = bundle[
            "target"
        ]

        self.sklearn_version = bundle[
            "sklearn_version"
        ]

    def predict(
        self,
        feature_values: dict[
            str,
            float,
        ],
    ) -> MLPredictionResult:

        missing_features = (
            set(self.features)
            - set(feature_values)
        )

        if missing_features:
            missing = ", ".join(
                sorted(
                    missing_features
                )
            )

            raise ValueError(
                f"Missing prediction features: "
                f"{missing}"
            )

        row = pd.DataFrame(
            [
                {
                    feature: (
                        feature_values[
                            feature
                        ]
                    )
                    for feature
                    in self.features
                }
            ]
        )

        prediction = float(
            self.model.predict(
                row
            )[0]
        )

        return MLPredictionResult(
            target=self.target,
            features={
                feature: float(
                    feature_values[
                        feature
                    ]
                )
                for feature
                in self.features
            },
            prediction=prediction,
        )

    def predict_pressure(
        self,
        pressure_psi: float,
        baseline_pressure_psi: float = 24.5,
    ) -> MLPredictionResult:

        pressure_distance = abs(
            pressure_psi
            - baseline_pressure_psi
        )

        return self.predict(
            {
                "absolute_parameter_delta_from_baseline": (
                    pressure_distance
                )
            }
        )

