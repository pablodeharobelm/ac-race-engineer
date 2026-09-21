from pathlib import Path

from ac_race_engineer.analysis.sweep_eda import (
    SweepEDA,
)


def main():

    sweep_directory = Path(
        "data/sweeps"
    )

    sweep_files = list(
        sweep_directory.glob(
            "*.csv"
        )
    )

    if not sweep_files:
        raise FileNotFoundError(
            "No sweep CSV files found. "
            "Run sweep_demo first."
        )

    latest_sweep = max(
        sweep_files,
        key=lambda path: (
            path.stat().st_mtime
        ),
    )

    analyzer = SweepEDA()

    report = analyzer.analyze(
        file_path=latest_sweep,
        parameter="front_pressure",
    )

    print()
    print("SWEEP EDA")
    print("=========")
    print()

    print(
        f"Dataset: {latest_sweep}"
    )

    print(
        f"Rows: {report.row_count}"
    )

    print(
        "Parameter range: "
        f"{report.minimum_parameter_value} "
        "-> "
        f"{report.maximum_parameter_value}"
    )

    print()

    print(
        "Minimum observed front slip:"
    )

    print(
        f"  Parameter: "
        f"{report.minimum_front_slip_value}"
    )

    print(
        f"  Slip: "
        f"{report.minimum_front_slip_angle_deg:.3f}"
    )

    print()
    print("CORRELATIONS")
    print("------------")

    for metric, correlation in report.correlations.items():

        if correlation is None:
            value = "N/A"
        else:
            value = f"{correlation:+.3f}"

        print(
            f"{metric}: {value}"
        )

    output_directory = Path(
        "data/analysis"
    )

    analyzer.plot_metric(
        file_path=latest_sweep,
        metric="front_pressure_psi",
        output_file=(
            output_directory
            / "front_pressure.png"
        ),
    )

    analyzer.plot_metric(
        file_path=latest_sweep,
        metric="front_slip_angle_deg",
        output_file=(
            output_directory
            / "front_slip.png"
        ),
    )

    print()
    print(
        "Charts created in "
        "data/analysis/"
    )


if __name__ == "__main__":
    main()