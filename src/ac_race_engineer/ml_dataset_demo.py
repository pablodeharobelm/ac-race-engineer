import pandas as pd

from ac_race_engineer.domain.setup import (
    CarSetup,
)
from ac_race_engineer.services.ml_dataset_builder import (
    MLDatasetBuilder,
)


def main():

    baseline = CarSetup(
        car_id="mazda_mx5_cup",
        name="Development baseline",
        values={
            "front_pressure": 24.5,
            "rear_pressure": 24.5,
            "front_camber": -2.5,
            "rear_camber": -2.0,
            "brake_bias": 0.64,
        },
    )

    builder = MLDatasetBuilder()

    result = builder.build(
        baseline_setup=baseline,
        parameter="front_pressure",
        values=[
            23.0,
            23.5,
            24.0,
            24.5,
            25.0,
            25.5,
            26.0,
        ],
        seeds=[
            10,
            20,
            30,
            40,
            50,
        ],
        hz=20,
        sample_count=600,
    )

    dataframe = pd.read_parquet(
        result.parquet_file
    )

    print()
    print("ML TRAINING DATASET")
    print("===================")
    print()

    print(
        f"Dataset ID: "
        f"{result.dataset_id}"
    )

    print(
        f"Rows: "
        f"{result.row_count}"
    )

    print(
        f"Sweeps: "
        f"{result.sweep_count}"
    )

    print(
        f"Seeds: "
        f"{result.seeds}"
    )

    print()
    print(
        dataframe[
            [
                "seed",
                "parameter_value",
                "absolute_parameter_delta_from_baseline",
                "front_pressure_psi",
                "front_slip_angle_deg",
                "front_rear_slip_delta",
            ]
        ].to_string(
            index=False
        )
    )

    print()

    print(
        f"CSV: "
        f"{result.csv_file}"
    )

    print(
        f"Parquet: "
        f"{result.parquet_file}"
    )


if __name__ == "__main__":
    main()

