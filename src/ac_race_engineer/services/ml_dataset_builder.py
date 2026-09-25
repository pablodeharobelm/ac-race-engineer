import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ac_race_engineer.domain.ml import (
    MLDatasetBuildResult,
)
from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.services.parameter_sweep import (
    ParameterSweepRunner,
)


class MLDatasetBuilder:

    def __init__(
        self,
        output_directory: str | Path = "data/ml",
        sweep_directory: str | Path = "data/sweeps",
        experiment_directory: str | Path = "data/experiments",
        session_directory: str | Path = "data/raw/experiments",
    ):
        self.output_directory = Path(
            output_directory
        )

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.sweep_runner = ParameterSweepRunner(
            output_directory=sweep_directory,
            experiment_directory=experiment_directory,
            session_directory=session_directory,
        )

    def build(
        self,
        baseline_setup: CarSetup,
        parameter: str,
        values: list[float],
        seeds: list[int],
        hz: int = 20,
        sample_count: int = 1200,
    ) -> MLDatasetBuildResult:

        if not seeds:
            raise ValueError(
                "At least one seed is required"
            )

        if not values:
            raise ValueError(
                "At least one parameter value is required"
            )

        if parameter not in baseline_setup.values:
            raise ValueError(
                f"Baseline setup does not contain parameter: "
                f"{parameter}"
            )

        baseline_value = (
            baseline_setup.values[
                parameter
            ]
        )

        rows = []

        sweep_count = 0

        for seed in seeds:

            sweep = self.sweep_runner.run(
                baseline_setup=baseline_setup,
                parameter=parameter,
                values=values,
                seed=seed,
                hz=hz,
                sample_count=sample_count,
            )

            sweep_count += 1

            for point in sweep.points:

                parameter_delta = (
                    point.parameter_value
                    - baseline_value
                )

                rows.append(
                    {
                        "sweep_id": sweep.sweep_id,
                        "experiment_id": (
                            point.experiment_id
                        ),
                        "car_id": sweep.car_id,
                        "parameter": parameter,
                        "seed": seed,
                        "baseline_value": (
                            baseline_value
                        ),
                        "parameter_value": (
                            point.parameter_value
                        ),
                        "parameter_delta_from_baseline": (
                            parameter_delta
                        ),
                        "absolute_parameter_delta_from_baseline": (
                            abs(parameter_delta)
                        ),
                        "front_pressure_psi": (
                            point.front_pressure_psi
                        ),
                        "rear_pressure_psi": (
                            point.rear_pressure_psi
                        ),
                        "front_rear_pressure_delta": (
                            point.front_pressure_psi
                            - point.rear_pressure_psi
                        ),
                        "front_core_temperature_c": (
                            point.front_core_temperature_c
                        ),
                        "rear_core_temperature_c": (
                            point.rear_core_temperature_c
                        ),
                        "front_rear_temperature_delta": (
                            point.front_core_temperature_c
                            - point.rear_core_temperature_c
                        ),
                        "front_brake_temperature_c": (
                            point.front_brake_temperature_c
                        ),
                        "rear_brake_temperature_c": (
                            point.rear_brake_temperature_c
                        ),
                        "front_rear_brake_temperature_delta": (
                            point.front_brake_temperature_c
                            - point.rear_brake_temperature_c
                        ),
                        "front_suspension_travel_mm": (
                            point.front_suspension_travel_mm
                        ),
                        "rear_suspension_travel_mm": (
                            point.rear_suspension_travel_mm
                        ),
                        "front_rear_suspension_delta": (
                            point.front_suspension_travel_mm
                            - point.rear_suspension_travel_mm
                        ),
                        "front_slip_angle_deg": (
                            point.front_slip_angle_deg
                        ),
                        "rear_slip_angle_deg": (
                            point.rear_slip_angle_deg
                        ),
                        "front_rear_slip_delta": (
                            point.front_slip_angle_deg
                            - point.rear_slip_angle_deg
                        ),
                        "front_limited_percentage": (
                            point.front_limited_percentage
                        ),
                        "rear_limited_percentage": (
                            point.rear_limited_percentage
                        ),
                        "maximum_lateral_g": (
                            point.maximum_lateral_g
                        ),
                    }
                )

        dataframe = pd.DataFrame(
            rows
        )

        dataframe = (
            dataframe
            .sort_values(
                [
                    "seed",
                    "parameter_value",
                ]
            )
            .reset_index(
                drop=True
            )
        )

        dataset_id = str(
            uuid.uuid4()
        )

        csv_file = (
            self.output_directory
            / f"{dataset_id}.csv"
        )

        parquet_file = (
            self.output_directory
            / f"{dataset_id}.parquet"
        )

        dataframe.to_csv(
            csv_file,
            index=False,
        )

        dataframe.to_parquet(
            parquet_file,
            index=False,
        )

        return MLDatasetBuildResult(
            dataset_id=dataset_id,
            created_at=datetime.now(UTC),
            car_id=baseline_setup.car_id,
            parameter=parameter,
            row_count=len(dataframe),
            sweep_count=sweep_count,
            seeds=seeds,
            csv_file=str(csv_file),
            parquet_file=str(parquet_file),
        )

