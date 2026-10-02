from datetime import (
    UTC,
    datetime,
)
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from ac_race_engineer.api.app import (
    create_app,
)
from ac_race_engineer.database.race_engineer_analyses import (
    RaceEngineerAnalysisRecord,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_report import (
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
        "persist": True,
        "session_id": "session-001",
    }


def pipeline_result():
    report = RaceEngineerReport(
        reference_lap_number=1,
        target_lap_number=2,
        trend=(
            RaceEngineerTrend.LOSING_TIME
        ),
        total_time_lost_seconds=0.30,
        total_time_gained_seconds=0.05,
        net_time_delta_seconds=0.25,
        corners_analyzed=0,
        corners_with_time_loss=0,
        corners_with_issues=0,
        recommendations_generated=0,
        recommendations_selected=0,
        recommendations_suppressed=0,
        primary_problem_corner=None,
        corners=(),
        focuses=(),
    )

    return SimpleNamespace(
        report=report,
        explanation=None,
    )


def stored_record(
    *,
    analysis_id: str = "analysis-001",
    session_id: str | None = "session-001",
) -> RaceEngineerAnalysisRecord:
    return RaceEngineerAnalysisRecord(
        id=analysis_id,
        session_id=session_id,
        reference_lap_number=1,
        target_lap_number=2,
        trend="losing_time",
        total_time_lost_seconds=0.30,
        total_time_gained_seconds=0.05,
        net_time_delta_seconds=0.25,
        primary_problem_corner=None,
        recommendations_generated=0,
        recommendations_selected=0,
        recommendations_suppressed=0,
        report_json={
            "reference_lap_number": 1,
            "target_lap_number": 2,
            "trend": "losing_time",
        },
        explanation_json=None,
        created_at=datetime(
            2026,
            10,
            2,
            15,
            0,
            tzinfo=UTC,
        ),
    )


def test_analysis_can_be_persisted() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    result = pipeline_result()

    pipeline.run.return_value = result

    persistence.save.return_value = (
        stored_record()
    )

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
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
        payload["analysis_id"]
        == "analysis-001"
    )

    persistence.save.assert_called_once_with(
        result,
        session_id="session-001",
    )


def test_analysis_is_not_persisted_by_default() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    result = pipeline_result()

    pipeline.run.return_value = result

    payload = request_payload()

    payload["persist"] = False

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
        )
    )

    response = client.post(
        "/v1/race-engineer/analyze",
        json=payload,
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()[
            "analysis_id"
        ]
        is None
    )

    persistence.save.assert_not_called()


def test_persist_requires_configured_manager() -> None:
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
        == 503
    )

    assert (
        "persistence"
        in response.json()[
            "detail"
        ].lower()
    )


def test_get_analysis() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    persistence.get_by_id.return_value = (
        stored_record()
    )

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
        )
    )

    response = client.get(
        
            "/v1/race-engineer/"
            "analyses/analysis-001"
        
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert (
        payload["analysis_id"]
        == "analysis-001"
    )

    assert (
        payload["session_id"]
        == "session-001"
    )

    assert (
        payload[
            "net_time_delta_seconds"
        ]
        == 0.25
    )

    assert (
        payload["report"][
            "trend"
        ]
        == "losing_time"
    )


def test_get_analysis_returns_404() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    persistence.get_by_id.return_value = None

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
        )
    )

    response = client.get(
        
            "/v1/race-engineer/"
            "analyses/missing"
        
    )

    assert (
        response.status_code
        == 404
    )


def test_list_recent_analyses() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    persistence.list_recent.return_value = [
        stored_record(
            analysis_id="analysis-002"
        ),
        stored_record(
            analysis_id="analysis-001"
        ),
    ]

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
        )
    )

    response = client.get(
        
            "/v1/race-engineer/"
            "analyses/recent?limit=2"
        
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert len(
        payload
    ) == 2

    assert (
        payload[0]["analysis_id"]
        == "analysis-002"
    )

    persistence.list_recent.assert_called_once_with(
        limit=2
    )


def test_recent_limit_is_validated() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
        )
    )

    response = client.get(
        
            "/v1/race-engineer/"
            "analyses/recent?limit=0"
        
    )

    assert (
        response.status_code
        == 422
    )

    persistence.list_recent.assert_not_called()


def test_list_analyses_for_session() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    persistence.list_for_session.return_value = [
        stored_record(
            analysis_id="analysis-a",
            session_id="session-a",
        ),
        stored_record(
            analysis_id="analysis-b",
            session_id="session-a",
        ),
    ]

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
        )
    )

    response = client.get(
        
            "/v1/race-engineer/"
            "analyses/session/session-a"
        
    )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert len(
        payload
    ) == 2

    assert all(
        item["session_id"]
        == "session-a"
        for item in payload
    )

    (
        persistence
        .list_for_session
        .assert_called_once_with(
            "session-a"
        )
    )


def test_history_endpoints_require_persistence() -> None:
    pipeline = MagicMock()

    client = TestClient(
        create_app(
            pipeline=pipeline
        )
    )

    response = client.get(
        
            "/v1/race-engineer/"
            "analyses/recent"
        
    )

    assert (
        response.status_code
        == 503
    )


def test_persistence_value_error_becomes_400() -> None:
    pipeline = MagicMock()
    persistence = MagicMock()

    pipeline.run.return_value = (
        pipeline_result()
    )

    persistence.save.side_effect = (
        ValueError(
            "session_id cannot be empty"
        )
    )

    payload = request_payload()

    payload["session_id"] = "   "

    client = TestClient(
        create_app(
            pipeline=pipeline,
            persistence_manager=persistence,
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
        "session_id"
        in response.json()[
            "detail"
        ]
    )