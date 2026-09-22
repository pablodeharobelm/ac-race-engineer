import pandas as pd
import pytest

from ac_race_engineer.analysis.feature_engineering import (
    SweepFeatureEngineer,
)


def create_dataset(
    tmp_path,
):
    dataframe = pd.DataFrame(
        {
            "parameter_value": [
                24.0,
                24.5,
                25.0,
            ],
            "experiment_id": [
                "exp-1",
                "exp-2",
                "exp-3",
            ],
            "front_pressure_psi": [
                24.2,
                24.7,
                25.2,
            ],
            "rear_pressure_psi": [
                24.7,
                24.7,
                24.7,
            ],
            "front_core_temperature_c": [
                70.0,
                71.0,
                72.0,
            ],
            "rear_core_temperature_c": [
                69.0,
                69.0,
                69.0,
            ],
            "front_brake_temperature_c": [
                200.0,
                200.0,
                200.0,
            ],
            "rear_brake_temperature_c": [
                160.0,
                160.0,
                160.0,
            ],
            "front_suspension_travel_mm": [
                60.0,
                60.0,
                60.0,
            ],
            "rear_suspension_travel_mm": [
                58.0,
                58.0,
                58.0,
            ],
            "front_slip_angle_deg": [
                3.2,
                3.0,
                3.2,
            ],
            "rear_slip_angle_deg": [
                2.8,
                2.8,
                2.8,
            ],
            "front_limited_percentage": [
                40.0,
                35.0,
                40.0,
            ],
            "rear_limited_percentage": [
                15.0,
                15.0,
                15.0,
            ],
            "maximum_lateral_g": [
                1.1,
                1.2,
                1.1,
            ],
        }
    )

    file_path = (
        tmp_path
        / "sweep.csv"
    )

    dataframe.to_csv(
        file_path,
        index=False,
    )

    return file_path


def test_feature_engineer_creates_features(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    engineer = SweepFeatureEngineer()

    dataframe = engineer.build(
        file_path=file_path,
        baseline_value=24.5,
    )

    assert (
        "front_rear_pressure_delta"
        in dataframe.columns
    )

    assert (
        "front_rear_slip_delta"
        in dataframe.columns
    )

    assert (
        "absolute_parameter_delta_from_baseline"
        in dataframe.columns
    )


def test_feature_engineer_calculates_parameter_delta(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    engineer = SweepFeatureEngineer()

    dataframe = engineer.build(
        file_path=file_path,
        baseline_value=24.5,
    )

    assert (
        dataframe.iloc[0][
            "parameter_delta_from_baseline"
        ]
        == pytest.approx(-0.5)
    )

    assert (
        dataframe.iloc[1][
            "parameter_delta_from_baseline"
        ]
        == pytest.approx(0.0)
    )

    assert (
        dataframe.iloc[2][
            "parameter_delta_from_baseline"
        ]
        == pytest.approx(0.5)
    )


def test_feature_engineer_calculates_balance_features(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    engineer = SweepFeatureEngineer()

    dataframe = engineer.build(
        file_path=file_path,
        baseline_value=24.5,
    )

    middle = dataframe.iloc[1]

    assert (
        middle[
            "front_rear_pressure_delta"
        ]
        == pytest.approx(0.0)
    )

    assert (
        middle[
            "front_rear_temperature_delta"
        ]
        == pytest.approx(2.0)
    )

    assert (
        middle[
            "front_rear_brake_temperature_delta"
        ]
        == pytest.approx(40.0)
    )

    assert (
        middle[
            "front_rear_suspension_delta"
        ]
        == pytest.approx(2.0)
    )

    assert (
        middle[
            "front_rear_slip_delta"
        ]
        == pytest.approx(0.2)
    )


def test_feature_engineer_saves_dataset(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    engineer = SweepFeatureEngineer()

    dataframe = engineer.build(
        file_path=file_path,
        baseline_value=24.5,
    )

    output_file = (
        tmp_path
        / "features.csv"
    )

    engineer.save(
        dataframe=dataframe,
        output_file=output_file,
    )

    assert output_file.exists()

    loaded = pd.read_csv(
        output_file
    )

    assert len(loaded) == 3