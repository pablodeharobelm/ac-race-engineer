from pathlib import Path
from typing import ClassVar

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from ac_race_engineer.domain.eda import (
    SweepEDAReport,
)


class SweepEDA:

    REQUIRED_COLUMNS: ClassVar[set[str]] = {
        "parameter_value",
        "experiment_id",
        "front_pressure_psi",
        "rear_pressure_psi",
        "front_core_temperature_c",
        "rear_core_temperature_c",
        "front_brake_temperature_c",
        "rear_brake_temperature_c",
        "front_suspension_travel_mm",
        "rear_suspension_travel_mm",
        "front_slip_angle_deg",
        "rear_slip_angle_deg",
        "front_limited_percentage",
        "rear_limited_percentage",
        "maximum_lateral_g",
    }

    def load(
        self,
        file_path: str | Path,
    ) -> pd.DataFrame:

        file_path = Path(
            file_path
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"Sweep dataset not found: "
                f"{file_path}"
            )

        dataframe = pd.read_csv(
            file_path
        )

        missing_columns = (
            self.REQUIRED_COLUMNS
            - set(dataframe.columns)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )

            raise ValueError(
                f"Missing sweep columns: "
                f"{missing}"
            )

        if dataframe.empty:
            raise ValueError(
                "Sweep dataset is empty"
            )

        dataframe = (
            dataframe
            .sort_values(
                "parameter_value"
            )
            .reset_index(
                drop=True
            )
        )

        return dataframe

    def analyze(
        self,
        file_path: str | Path,
        parameter: str,
    ) -> SweepEDAReport:

        dataframe = self.load(
            file_path
        )

        numeric_columns = (
            dataframe
            .select_dtypes(
                include="number"
            )
            .columns
        )

        correlations = {}

        for column in numeric_columns:

            if column == "parameter_value":
                continue

            paired_data = dataframe[
                [
                    "parameter_value",
                    column,
                ]
            ].dropna()

            parameter_variation = (
                paired_data[
                    "parameter_value"
                ].nunique()
            )

            metric_variation = (
                paired_data[
                    column
                ].nunique()
            )

            if (
                len(paired_data) < 2
                or parameter_variation < 2
                or metric_variation < 2
            ):
                correlations[column] = None
                continue

            correlation = (
                paired_data[
                    "parameter_value"
                ].corr(
                    paired_data[column]
                )
            )

            if pd.isna(
                correlation
            ):
                correlations[column] = None

            else:
                correlations[column] = float(
                    correlation
                )

        minimum_slip_index = (
            dataframe[
                "front_slip_angle_deg"
            ].idxmin()
        )

        minimum_slip_row = (
            dataframe.loc[
                minimum_slip_index
            ]
        )

        return SweepEDAReport(
            parameter=parameter,
            row_count=len(
                dataframe
            ),
            minimum_parameter_value=float(
                dataframe[
                    "parameter_value"
                ].min()
            ),
            maximum_parameter_value=float(
                dataframe[
                    "parameter_value"
                ].max()
            ),
            minimum_front_slip_value=float(
                minimum_slip_row[
                    "parameter_value"
                ]
            ),
            minimum_front_slip_angle_deg=float(
                minimum_slip_row[
                    "front_slip_angle_deg"
                ]
            ),
            correlations=correlations,
        )

    def plot_metric(
        self,
        file_path: str | Path,
        metric: str,
        output_file: str | Path,
    ) -> Path:

        dataframe = self.load(
            file_path
        )

        if metric not in dataframe.columns:
            raise ValueError(
                f"Unknown metric: {metric}"
            )

        if not pd.api.types.is_numeric_dtype(
            dataframe[metric]
        ):
            raise ValueError(
                f"Metric is not numeric: "
                f"{metric}"
            )

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        figure, axis = plt.subplots()

        axis.plot(
            dataframe[
                "parameter_value"
            ],
            dataframe[metric],
            marker="o",
        )

        axis.set_xlabel(
            "Parameter value"
        )

        axis.set_ylabel(
            metric
        )

        axis.set_title(
            f"Parameter sweep: {metric}"
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