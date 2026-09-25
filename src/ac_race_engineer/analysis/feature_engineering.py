from pathlib import Path

import pandas as pd

from ac_race_engineer.analysis.sweep_eda import (
    SweepEDA,
)


class SweepFeatureEngineer:

    def __init__(self):
        self.eda = SweepEDA()

    def build(
        self,
        file_path: str | Path,
        baseline_value: float,
    ) -> pd.DataFrame:

        dataframe = self.eda.load(
            file_path
        ).copy()

        dataframe[
            "parameter_delta_from_baseline"
        ] = (
            dataframe["parameter_value"]
            - baseline_value
        )

        dataframe[
            "absolute_parameter_delta_from_baseline"
        ] = (
            dataframe[
                "parameter_delta_from_baseline"
            ].abs()
        )

        dataframe[
            "front_rear_pressure_delta"
        ] = (
            dataframe["front_pressure_psi"]
            - dataframe["rear_pressure_psi"]
        )

        dataframe[
            "front_rear_temperature_delta"
        ] = (
            dataframe[
                "front_core_temperature_c"
            ]
            - dataframe[
                "rear_core_temperature_c"
            ]
        )

        dataframe[
            "front_rear_brake_temperature_delta"
        ] = (
            dataframe[
                "front_brake_temperature_c"
            ]
            - dataframe[
                "rear_brake_temperature_c"
            ]
        )

        dataframe[
            "front_rear_suspension_delta"
        ] = (
            dataframe[
                "front_suspension_travel_mm"
            ]
            - dataframe[
                "rear_suspension_travel_mm"
            ]
        )

        dataframe[
            "front_rear_slip_delta"
        ] = (
            dataframe[
                "front_slip_angle_deg"
            ]
            - dataframe[
                "rear_slip_angle_deg"
            ]
        )

        return dataframe

    def save(
        self,
        dataframe: pd.DataFrame,
        output_file: str | Path,
    ) -> Path:

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

