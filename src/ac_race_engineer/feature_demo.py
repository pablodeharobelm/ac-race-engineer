from pathlib import Path

from ac_race_engineer.analysis.feature_engineering import (
    SweepFeatureEngineer,
)


def main():

    sweep_directory = Path(
        "data/sweeps"
    )

    files = list(
        sweep_directory.glob(
            "*.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            "No sweep datasets found"
        )

    latest = max(
        files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    engineer = SweepFeatureEngineer()

    dataframe = engineer.build(
        file_path=latest,
        baseline_value=24.5,
    )

    columns = [
        "parameter_value",
        "parameter_delta_from_baseline",
        "absolute_parameter_delta_from_baseline",
        "front_pressure_psi",
        "front_rear_pressure_delta",
        "front_slip_angle_deg",
        "front_rear_slip_delta",
    ]

    print()
    print("FEATURE DATASET")
    print("===============")
    print()

    print(
        dataframe[
            columns
        ].to_string(
            index=False
        )
    )

    output = engineer.save(
        dataframe=dataframe,
        output_file=(
            "data/analysis/"
            "feature_dataset.csv"
        ),
    )

    print()
    print(
        f"Feature dataset created: "
        f"{output}"
    )


if __name__ == "__main__":
    main()

