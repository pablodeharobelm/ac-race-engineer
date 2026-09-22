from datetime import UTC, datetime

from ac_race_engineer.analysis.ml_run_analytics import (
    MLRunAnalytics,
)
from ac_race_engineer.domain.ml_tracking import (
    MLRunMetrics,
    MLRunRecord,
)
from ac_race_engineer.repositories.ml_run_repository import (
    MLRunRepository,
)


def create_run(
    run_id: str,
    mae: float,
    rmse: float,
    r2: float,
) -> MLRunRecord:

    return MLRunRecord(
        run_id=run_id,
        created_at=datetime.now(UTC),
        model_name="linear_regression",
        model_id=f"model-{run_id}",
        dataset_file="dataset.parquet",
        model_file=f"{run_id}.joblib",
        report_file=f"{run_id}.json",
        target="front_slip_angle_deg",
        features=[
            "absolute_parameter_delta_from_baseline"
        ],
        train_rows=28,
        test_rows=7,
        train_seeds=[
            10,
            20,
            30,
            40,
        ],
        test_seeds=[
            50,
        ],
        metrics=MLRunMetrics(
            mae=mae,
            rmse=rmse,
            r2=r2,
        ),
        parameters={},
        library_versions={},
    )


def create_repository(
    tmp_path,
):
    repository = MLRunRepository(
        tmp_path / "runs.jsonl"
    )

    repository.save(
        create_run(
            "run-1",
            mae=0.02,
            rmse=0.03,
            r2=0.95,
        )
    )

    repository.save(
        create_run(
            "run-2",
            mae=0.01,
            rmse=0.02,
            r2=0.98,
        )
    )

    return repository


def test_ml_run_analytics_builds_dataframe(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    analytics = MLRunAnalytics(
        repository=repository
    )

    dataframe = analytics.dataframe()

    assert len(dataframe) == 2

    assert (
        "mae"
        in dataframe.columns
    )

    assert (
        "r2"
        in dataframe.columns
    )


def test_ml_run_analytics_generates_report(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    analytics = MLRunAnalytics(
        repository=repository
    )

    report = analytics.analyze()

    assert report.run_count == 2

    assert report.minimum_mae == 0.01
    assert report.maximum_r2 == 0.98

    assert (
        report.dataset_file_count
        == 1
    )


def test_ml_run_analytics_saves_csv(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    analytics = MLRunAnalytics(
        repository=repository
    )

    output_file = (
        tmp_path
        / "analytics.csv"
    )

    analytics.save_csv(
        output_file
    )

    assert output_file.exists()


def test_ml_run_analytics_creates_plots(
    tmp_path,
):
    repository = create_repository(
        tmp_path
    )

    analytics = MLRunAnalytics(
        repository=repository
    )

    error_plot = (
        tmp_path
        / "errors.png"
    )

    r2_plot = (
        tmp_path
        / "r2.png"
    )

    analytics.plot_metrics(
        error_plot
    )

    analytics.plot_r2(
        r2_plot
    )

    assert error_plot.exists()
    assert r2_plot.exists()