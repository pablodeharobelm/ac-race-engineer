from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from ac_race_engineer.api.app import (
    create_app,
)
from ac_race_engineer.telemetry.assetto_corsa.recommendations import (
    RecommendationPriority,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_coaching_strategy import (
    CoachingFocusLevel,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_diagnostics import (
    DrivingPhase,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_driving_recommendations import (
    DrivingRecommendationType,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
    RaceEngineerCornerSummary,
    RaceEngineerFocusSummary,
    RaceEngineerReport,
    RaceEngineerTrend,
)


def request_payload() -> dict:
    return {
        "reference_lap_number": 1,
        "target_lap_number": 2,
        "reference_trace": [
            {
                "progress": 0.0,
                "elapsed_seconds": 0.0,
                "speed_kmh": 100.0,
                "throttle": 1.0,
                "brake": 0.0,
                "steering_angle_deg": 0.0,
            },
            {
                "progress": 1.0,
                "elapsed_seconds": 100.0,
                "speed_kmh": 120.0,
                "throttle": 1.0,
                "brake": 0.0,
                "steering_angle_deg": 0.0,
            },
        ],
        "target_trace": [
            {
                "progress": 0.0,
                "elapsed_seconds": 0.0,
                "speed_kmh": 100.0,
                "throttle": 1.0,
                "brake": 0.0,
                "steering_angle_deg": 0.0,
            },
            {
                "progress": 1.0,
                "elapsed_seconds": 101.0,
                "speed_kmh": 118.0,
                "throttle": 1.0,
                "brake": 0.0,
                "steering_angle_deg": 0.0,
            },
        ],
        "grid_points": 201,
        "explain": False,
        "language": "es",
    }


def pipeline_result():
    report = RaceEngineerReport(
        reference_lap_number=1,
        target_lap_number=2,
        trend=(
            RaceEngineerTrend.LOSING_TIME
        ),
        total_time_lost_seconds=0.35,
        total_time_gained_seconds=0.10,
        net_time_delta_seconds=0.25,
        corners_analyzed=1,
        corners_with_time_loss=1,
        corners_with_issues=1,
        recommendations_generated=2,
        recommendations_selected=1,
        recommendations_suppressed=1,
        primary_problem_corner=1,
        corners=(
            RaceEngineerCornerSummary(
                corner_number=1,
                time_lost_seconds=0.35,
                time_gained_seconds=0.0,
                entry_time_loss_seconds=0.20,
                exit_time_loss_seconds=0.15,
                dominant_phase=(
                    DrivingPhase.ENTRY
                ),
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
                issue_count=2,
            ),
        ),
        focuses=(
            RaceEngineerFocusSummary(
                rank=1,
                focus_level=(
                    CoachingFocusLevel.PRIMARY
                ),
                corner_number=1,
                recommendation_type=(
                    DrivingRecommendationType
                    .BRAKING_POINT
                ),
                priority=(
                    RecommendationPriority.HIGH
                ),
                phase=(
                    DrivingPhase.ENTRY
                ),
                title="Brake slightly later",
                instruction=(
                    "Move the braking point "
                    "slightly later."
                ),
                rationale=(
                    "The target brakes earlier "
                    "than the reference."
                ),
                diagnostic_code=(
                    "BRAKING_TOO_EARLY"
                ),
                corner_time_loss_seconds=0.35,
                minimum_speed_delta_kmh=-6.0,
                apex_speed_delta_kmh=-5.0,
                exit_speed_delta_kmh=-4.0,
            ),
        ),
    )

    return SimpleNamespace(
        report=report,
        explanation=None,
    )


def test_health_endpoint() -> None:
    pipeline = MagicMock()

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.get(
        "/health"
    )

    assert (
        response.status_code
        == 200
    )

    assert response.json() == {
        "status": "ok",
        "service": "ac-race-engineer",
        "version": "0.1.0",
    }


def test_analyze_endpoint() -> None:
    pipeline = MagicMock()

    pipeline.run.return_value = (
        pipeline_result()
    )

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=request_payload(),
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert (
        payload[
            "reference_lap_number"
        ]
        == 1
    )

    assert (
        payload[
            "target_lap_number"
        ]
        == 2
    )

    assert (
        payload[
            "trend"
        ]
        == "losing_time"
    )

    assert (
        payload[
            "primary_problem_corner"
        ]
        == 1
    )

    assert (
        payload[
            "recommendations_selected"
        ]
        == 1
    )

    assert (
        payload["corners"][0][
            "apex_speed_delta_kmh"
        ]
        == -5.0
    )

    assert (
        payload["focuses"][0][
            "diagnostic_code"
        ]
        == "BRAKING_TOO_EARLY"
    )


def test_converts_request_to_domain_trace() -> None:
    pipeline = MagicMock()

    pipeline.run.return_value = (
        pipeline_result()
    )

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    client.post(
        "/v1/race-engineer/analyze",
        json=request_payload(),
    )

    call = (
        pipeline.run.call_args.kwargs
    )

    reference_trace = (
        call["reference_trace"]
    )

    target_trace = (
        call["target_trace"]
    )

    assert len(
        reference_trace
    ) == 2

    assert len(
        target_trace
    ) == 2

    assert (
        reference_trace[0].progress
        == 0.0
    )

    assert (
        target_trace[-1]
        .elapsed_seconds
        == 101.0
    )


def test_passes_pipeline_options() -> None:
    pipeline = MagicMock()

    pipeline.run.return_value = (
        pipeline_result()
    )

    payload = request_payload()

    payload[
        "grid_points"
    ] = 301

    payload[
        "language"
    ] = "en"

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    client.post(
        "/v1/race-engineer/analyze",
        json=payload,
    )

    pipeline.run.assert_called_once()

    call = (
        pipeline.run.call_args.kwargs
    )

    assert (
        call[
            "reference_lap_number"
        ]
        == 1
    )

    assert (
        call[
            "target_lap_number"
        ]
        == 2
    )

    assert (
        call["grid_points"]
        == 301
    )

    assert (
        call["language"]
        == "en"
    )

    assert (
        call["explain"]
        is False
    )


def test_rejects_same_lap_number() -> None:
    pipeline = MagicMock()

    payload = request_payload()

    payload[
        "target_lap_number"
    ] = 1

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=payload,
    )

    assert (
        response.status_code
        == 400
    )

    assert (
        "must be different"
        in response.json()[
            "detail"
        ]
    )

    pipeline.run.assert_not_called()


def test_rejects_invalid_trace_sample() -> None:
    pipeline = MagicMock()

    payload = request_payload()

    payload[
        "reference_trace"
    ][0][
        "throttle"
    ] = 1.5

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )

    pipeline.run.assert_not_called()


def test_rejects_trace_with_less_than_two_samples() -> None:
    pipeline = MagicMock()

    payload = request_payload()

    payload[
        "reference_trace"
    ] = payload[
        "reference_trace"
    ][:1]

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=payload,
    )

    assert (
        response.status_code
        == 422
    )

    pipeline.run.assert_not_called()


def test_converts_pipeline_value_error_to_400() -> None:
    pipeline = MagicMock()

    pipeline.run.side_effect = (
        ValueError(
            "Invalid trace progress"
        )
    )

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=request_payload(),
    )

    assert (
        response.status_code
        == 400
    )

    assert response.json() == {
        "detail": (
            "Invalid trace progress"
        )
    }


def test_reports_unconfigured_llm_as_503() -> None:
    pipeline = MagicMock()

    pipeline.run.side_effect = (
        ValueError(
            "explain=True requires "
            "an explanation_service"
        )
    )

    payload = request_payload()

    payload[
        "explain"
    ] = True

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=payload,
    )

    assert (
        response.status_code
        == 503
    )

    assert response.json() == {
        "detail": (
            "LLM explanation service "
            "is not configured"
        )
    }


def test_openapi_contains_analyze_endpoint() -> None:
    pipeline = MagicMock()

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.get(
        "/openapi.json"
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        "/v1/race-engineer/analyze"
        in response.json()[
            "paths"
        ]
    )