from pathlib import Path

from ac_race_engineer.analysis.ml_run_analytics import (
    MLRunAnalytics,
)


def main():

    analytics = MLRunAnalytics()

    report = analytics.analyze()

    dataframe = analytics.dataframe()

    print()
    print("ML RUN ANALYTICS")
    print("================")
    print()

    print(
        f"Runs: "
        f"{report.run_count}"
    )

    print(
        f"Models: "
        f"{report.model_names}"
    )

    print()

    print(
        f"Average MAE: "
        f"{report.average_mae:.6f}"
    )

    print(
        f"Average RMSE: "
        f"{report.average_rmse:.6f}"
    )

    print(
        f"Average R2: "
        f"{report.average_r2:.6f}"
    )

    print()

    print(
        f"Minimum MAE: "
        f"{report.minimum_mae:.6f}"
    )

    print(
        f"Maximum R2: "
        f"{report.maximum_r2:.6f}"
    )

    print()

    print(
        dataframe[
            [
                "run_id",
                "model_name",
                "mae",
                "rmse",
                "r2",
            ]
        ].to_string(
            index=False
        )
    )

    output_directory = Path(
        "data/analysis/ml_tracking"
    )

    csv_file = analytics.save_csv(
        output_directory
        / "runs.csv"
    )

    error_plot = (
        analytics.plot_metrics(
            output_directory
            / "error_evolution.png"
        )
    )

    r2_plot = analytics.plot_r2(
        output_directory
        / "r2_evolution.png"
    )

    print()

    print(
        f"CSV: "
        f"{csv_file}"
    )

    print(
        f"Errors chart: "
        f"{error_plot}"
    )

    print(
        f"R2 chart: "
        f"{r2_plot}"
    )


if __name__ == "__main__":
    main()