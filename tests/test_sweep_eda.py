import pandas as pd
import pytest

from ac_race_engineer.analysis.sweep_eda import (
    SweepEDA,
)


def create_dataset(
    tmp_path,
):
    dataframe = pd.DataFrame(
        {
            "parameter_value": [
                23.0,
                24.5,
                26.0,
            ],
            "experiment_id": [
                "exp-1",
                "exp-2",
                "exp-3",
            ],
            "front_pressure_psi": [
                23.2,
                24.7,
                26.2,
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
                3.4,
                3.0,
                3.5,
            ],
            "rear_slip_angle_deg": [
                2.8,
                2.8,
                2.8,
            ],
            "front_limited_percentage": [
                40.0,
                35.0,
                42.0,
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


def test_sweep_eda_loads_dataset(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    analyzer = SweepEDA()

    dataframe = analyzer.load(
        file_path
    )

    assert len(dataframe) == 3

    assert (
        dataframe.iloc[0][
            "parameter_value"
        ]
        == 23.0
    )


def test_sweep_eda_finds_minimum_front_slip(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    analyzer = SweepEDA()

    report = analyzer.analyze(
        file_path=file_path,
        parameter="front_pressure",
    )

    assert (
        report.minimum_front_slip_value
        == 24.5
    )

    assert (
        report.minimum_front_slip_angle_deg
        == pytest.approx(
            3.0
        )
    )


def test_sweep_eda_calculates_correlation(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    analyzer = SweepEDA()

    report = analyzer.analyze(
        file_path=file_path,
        parameter="front_pressure",
    )

    correlation = (
        report.correlations[
            "front_pressure_psi"
        ]
    )

    assert correlation is not None

    assert correlation > 0.99

    assert (
    report.correlations[
        "rear_pressure_psi"
    ]
    is None
)


def test_sweep_eda_creates_plot(
    tmp_path,
):
    file_path = create_dataset(
        tmp_path
    )

    analyzer = SweepEDA()

    output_file = (
        tmp_path
        / "front_slip.png"
    )

    analyzer.plot_metric(
        file_path=file_path,
        metric="front_slip_angle_deg",
        output_file=output_file,
    )

    assert output_file.exists()