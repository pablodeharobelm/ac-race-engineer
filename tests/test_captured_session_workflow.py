import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from streamlit.testing.v1 import AppTest

from ac_race_engineer.api.app import create_app
from ac_race_engineer.database.base import Base
from ac_race_engineer.database.models import LapTraceRecord
from ac_race_engineer.database.race_engineer_analyses import race_engineer_analysis_metadata
from ac_race_engineer.database.session import create_database_engine, create_session_factory
from ac_race_engineer.demo_session import capture_demo_session


@pytest.fixture
def captured_session(tmp_path):
    engine = create_database_engine(f"sqlite+pysqlite:///{(tmp_path / 'demo.db').as_posix()}")
    Base.metadata.create_all(engine)
    race_engineer_analysis_metadata.create_all(engine)
    factory = create_session_factory(engine)
    session_id, statistics = capture_demo_session(engine, trace_directory=tmp_path / "traces")
    with TestClient(create_app(session_factory=factory)) as client:
        yield client, session_id, statistics, factory
    engine.dispose()


def test_capture_to_api_analysis_and_history(captured_session):
    client, session_id, statistics, _ = captured_session
    assert statistics.laps_saved == statistics.traces_saved == 2
    assert statistics.sectors_saved == 6
    response = client.get("/v1/sessions")
    assert response.status_code == 200
    assert response.json()[0]["session_id"] == session_id
    assert response.json()[0]["lap_count"] == response.json()[0]["trace_count"] == 2
    laps = client.get(f"/v1/sessions/{session_id}/laps").json()
    assert [lap["lap_number"] for lap in laps] == [1, 2]
    assert all(lap["trace_available"] for lap in laps)
    assert laps[1]["lap_time_ms"] > laps[0]["lap_time_ms"]
    trace = client.get(f"/v1/sessions/{session_id}/laps/1/trace").json()
    assert len(trace["samples"]) == 201
    assert trace["samples"][0]["progress"] == 0
    assert trace["samples"][-1]["progress"] == 1
    response = client.post(f"/v1/sessions/{session_id}/analyze", json={
        "reference_lap_number": 1, "target_lap_number": 2,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["analysis_id"]
    assert result["net_time_delta_seconds"] > 0
    assert result["corners_analyzed"] > 0
    assert result["recommendations_generated"] > 0
    stored = client.get(f"/v1/race-engineer/analyses/{result['analysis_id']}").json()
    assert stored["session_id"] == session_id
    assert stored["report"]["corners"] == result["corners"]
    assert len(client.get(f"/v1/race-engineer/analyses/session/{session_id}").json()) == 1


def test_no_persistence_and_input_validation(captured_session):
    client, session_id, _, _ = captured_session
    path = f"/v1/sessions/{session_id}/analyze"
    assert client.post(path, json={"reference_lap_number": 1, "target_lap_number": 1}).status_code == 400
    assert client.post(path, json={"reference_lap_number": 0, "target_lap_number": 2}).status_code == 422
    assert client.post(path, json={"reference_lap_number": 1, "target_lap_number": 99}).status_code == 404
    assert client.get("/v1/sessions/missing/laps").status_code == 404
    assert client.get("/v1/sessions?limit=101").status_code == 422
    response = client.post(path, json={
        "reference_lap_number": 1, "target_lap_number": 2, "persist": False,
    })
    assert response.status_code == 200
    assert response.json()["analysis_id"] is None
    assert client.get("/v1/race-engineer/analyses/recent").json() == []


@pytest.mark.parametrize("damage", ["missing", "corrupt", "wrong_session", "version", "invalid_samples"])
def test_unavailable_traces_do_not_save_analysis(captured_session, damage):
    client, session_id, _, factory = captured_session
    with factory() as session:
        records = list(session.scalars(select(LapTraceRecord).order_by(LapTraceRecord.lap_number)))
        record = records[0]
        if damage == "missing":
            Path(record.parquet_path).unlink()
        elif damage == "corrupt":
            Path(record.parquet_path).write_bytes(b"not parquet")
        elif damage == "wrong_session":
            record.parquet_path = records[1].parquet_path
        elif damage == "invalid_samples":
            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pq.ParquetFile(record.parquet_path).read()
            rows = table.to_pylist()
            rows[0]["speed_kmh"] = float("nan")
            pq.write_table(pa.Table.from_pylist(rows), record.parquet_path)
        else:
            record.schema_version = 99
        session.commit()
    response = client.post(f"/v1/sessions/{session_id}/analyze", json={
        "reference_lap_number": 1, "target_lap_number": 2,
    })
    assert response.status_code == 409, response.text
    assert client.get("/v1/race-engineer/analyses/recent").json() == []
    if damage in ("missing", "version"):
        laps = client.get(f"/v1/sessions/{session_id}/laps").json()
        assert not laps[0]["trace_available"]
        assert laps[0]["unavailable_reason"]


def test_dashboard_selects_saved_laps_and_retains_results(captured_session, monkeypatch):
    client, _, _, _ = captured_session

    class Response:
        def __init__(self, response):
            self.response = response

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return self.response.content

    def in_process_request(request, timeout):
        url = urlsplit(request.full_url)
        response = client.request(request.method, url.path + (f"?{url.query}" if url.query else ""),
                                  json=json.loads(request.data) if request.data else None)
        if response.status_code >= 400:
            raise HTTPError(request.full_url, response.status_code, "API error", {}, io.BytesIO(response.content))
        return Response(response)

    monkeypatch.setattr("ac_race_engineer.dashboard.api_client.urlopen", in_process_request)
    from ac_race_engineer.dashboard.saved_sessions import _laps, _sessions
    _laps.clear()
    _sessions.clear()
    dashboard = Path(__file__).parents[1] / "src/ac_race_engineer/dashboard/app.py"
    app = AppTest.from_file(str(dashboard), default_timeout=30).run()
    assert not app.exception
    assert not app.error
    assert app.selectbox(key="captured-session").value
    next(button for button in app.button if button.label == "Comparar mis vueltas").click().run()
    assert not app.exception
    assert not app.error
    assert any(item.value == "Análisis completado." for item in app.success)
    app.run()
    assert any(item.value == "Análisis completado." for item in app.success)
    assert any("Mejora la velocidad en el vértice" in element.value for element in app.markdown)
    assert not any("Improve apex speed" in element.value for element in app.markdown)
    next(widget for widget in app.segmented_control if widget.label == "Qué quieres comparar").set_value("Diferencia de tiempo").run()
    assert not app.exception
    assert len(client.get("/v1/race-engineer/analyses/recent").json()) == 1
    app.segmented_control[0].set_value("Historial").run()
    assert not app.exception
    assert not app.error
    assert any("Abrir un análisis guardado" == widget.label for widget in app.selectbox)
    app.segmented_control[0].set_value("Importar datos").run()
    next(widget for widget in app.segmented_control if widget.label == "Cómo quieres cargar las vueltas").set_value("Datos de ejemplo").run()
    next(button for button in app.button if button.label == "Comparar vueltas").click().run()
    assert not app.exception
    assert not app.error
    next(widget for widget in app.segmented_control if widget.label == "Qué quieres comparar").set_value("Freno").run()
    assert not app.exception
    assert any(item.value == "Análisis completado." for item in app.success)
    app.segmented_control[0].set_value("Conducción").run()
    next(widget for widget in app.segmented_control if widget.label == "Qué quieres reproducir").set_value("Vueltas guardadas").run()
    next(button for button in app.button if button.label == "Cargar vuelta").click().run()
    assert not app.exception
    assert not app.error
    assert any(metric.label == "Marcha" and metric.value != "Sin datos" for metric in app.metric)
    next(button for button in app.button if button.label == "Reproducir").click().run()
    assert app.session_state["driving_playback"].playing
    assert not app.exception


def test_unconfigured_and_unmigrated_database(tmp_path):
    with TestClient(create_app()) as client:
        assert client.get("/v1/sessions").status_code == 503
    engine = create_database_engine(f"sqlite+pysqlite:///{(tmp_path / 'empty.db').as_posix()}")
    try:
        with TestClient(create_app(session_factory=create_session_factory(engine))) as client:
            response = client.get("/v1/sessions")
            assert response.status_code == 503
            assert "migrations" in response.json()["detail"]
    finally:
        engine.dispose()


def test_local_app_disposes_owned_engine(monkeypatch):
    from unittest.mock import MagicMock

    from ac_race_engineer.api.app import create_local_app

    engine = MagicMock()
    monkeypatch.setattr("ac_race_engineer.api.app.create_database_engine", lambda: engine)
    with TestClient(create_local_app()) as client:
        assert client.get("/health").status_code == 200
        engine.dispose.assert_not_called()
    engine.dispose.assert_called_once()
