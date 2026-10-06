from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ac_race_engineer.dashboard.driving import (
    Playback,
    delta_style,
    demo_laps,
    interpolate,
    reference_time,
)


def test_playback_pause_rate_and_finish():
    playback = Playback(playing=True, updated_at=10)
    playback.advance(12, 20)
    assert playback.position == 2
    playback.playing = False
    playback.advance(18, 20)
    assert playback.position == 2
    playback.playing = True
    playback.rate = 4
    playback.advance(19, 20)
    assert playback.position == 6
    playback.advance(30, 20)
    assert playback.position == 20
    assert not playback.playing


def test_same_position_delta_and_interpolation():
    reference, target = demo_laps()
    for point in reference:
        assert reference_time(point.progress) == pytest.approx(point.elapsed_seconds)
    assert target[-1].elapsed_seconds - reference_time(1) > 0.9
    midpoint = (target[60].elapsed_seconds + target[61].elapsed_seconds) / 2
    assert interpolate(target, midpoint)["progress"] == pytest.approx((target[60].progress + target[61].progress) / 2)
    assert interpolate(target, -1)["progress"] == 0
    assert interpolate(target, 10000)["progress"] == 1


def test_driving_works_without_api_and_retains_pause(monkeypatch):
    monkeypatch.setattr("ac_race_engineer.dashboard.app._render_connection_status", lambda client: None)
    dashboard = Path(__file__).parents[1] / "src/ac_race_engineer/dashboard/app.py"
    app = AppTest.from_file(str(dashboard), default_timeout=30)
    app.session_state["driving_playback"] = Playback(position=10, updated_at=0)
    app.run()
    app.segmented_control[0].set_value("Conducción").run()
    assert not app.exception
    assert any(metric.label == "Velocidad" for metric in app.metric)
    next(button for button in app.button if button.label == "Reproducir").click().run()
    assert app.session_state["driving_playback"].playing
    next(button for button in app.button if button.label == "Pausar").click().run()
    assert not app.session_state["driving_playback"].playing
    position = app.session_state["driving_playback"].position
    app.run()
    assert app.session_state["driving_playback"].position == position
    next(button for button in app.button if button.label == "Reiniciar").click().run()
    assert app.session_state["driving_playback"].position == 0
    assert not app.exception


def test_delta_colors_keep_gain_loss_and_neutral_distinct():
    assert delta_style(0.1) == ("red", "Pierdes tiempo")
    assert delta_style(-0.1) == ("green", "Ganas tiempo")
    assert delta_style(0.0001) == ("gray", "Al mismo ritmo")


def test_reference_interpolates_irregular_progress():
    from ac_race_engineer.telemetry.assetto_corsa.trace import DrivingTraceSample
    trace = tuple(DrivingTraceSample(p, t, 100, 1, 0, 0) for p, t in ((0.1, 4), (0.2, 10), (0.9, 40)))
    assert reference_time(0.15, trace) == pytest.approx(7)
    assert reference_time(0.55, trace) == pytest.approx(25)


def test_replay_keeps_discrete_gears_and_interpolates_clutch():
    from ac_race_engineer.telemetry.assetto_corsa.trace import DrivingTraceSample
    trace = (DrivingTraceSample(0, 0, 100, 1, 0, 0, gear=2, clutch=0),
             DrivingTraceSample(1, 2, 100, 1, 0, 0, gear=3, clutch=1))
    assert interpolate(trace, 1)["gear"] == 2
    assert interpolate(trace, 1)["clutch"] == 0.5
    assert interpolate(trace, 2)["gear"] == 3


def test_replay_interpolates_signed_steering_without_changing_convention():
    from ac_race_engineer.telemetry.assetto_corsa.trace import DrivingTraceSample
    trace = (DrivingTraceSample(0, 0, 100, 1, 0, -30), DrivingTraceSample(1, 2, 100, 1, 0, 10))
    assert interpolate(trace, 1)["steering_angle_deg"] == -10
    assert interpolate(trace, -1)["steering_angle_deg"] == -30
    assert interpolate(trace, 3)["steering_angle_deg"] == 10


def test_live_simulator_hides_values_when_disconnected():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/ac_race_engineer/dashboard/app.py"), default_timeout=30).run()
    app.segmented_control[0].set_value("Conducción").run()
    next(widget for widget in app.segmented_control if widget.label == "Qué quieres reproducir").set_value("En directo").run()
    assert not app.exception
    assert any(metric.label == "Velocidad" for metric in app.metric)
    next(widget for widget in app.selectbox if widget.label == "Estado que quieres probar").set_value("Desconectado").run()
    assert not app.exception
    assert not app.metric
    assert any(item.value == "Desconectado" for item in app.warning)


def test_imported_replay_seek_and_estimation_warning(monkeypatch):
    from ac_race_engineer.dashboard.app import DEFAULT_REFERENCE_TRACE

    monkeypatch.setattr("ac_race_engineer.dashboard.app._render_connection_status", lambda client: None)
    dashboard = Path(__file__).parents[1] / "src/ac_race_engineer/dashboard/app.py"
    app = AppTest.from_file(str(dashboard), default_timeout=30).run()
    app.segmented_control[0].set_value("Conducción").run()
    next(widget for widget in app.segmented_control if widget.label == "Qué quieres reproducir").set_value("Vueltas importadas").run()
    assert any("Primero compara" in item.value for item in app.info)
    rows = [dict(row, gear=3, clutch=0.25) for row in DEFAULT_REFERENCE_TRACE]
    app.session_state["imported_analysis"] = ({"time_estimated": True}, rows, rows)
    app.run()
    assert not app.exception
    assert any("aproximados" in item.value for item in app.warning)
    next(widget for widget in app.slider if widget.label == "Saltar a un momento (segundos)").set_value(10.0).run()
    assert app.session_state["driving_playback"].position == 10.0
    assert not app.session_state["driving_playback"].playing
    assert next(metric.value for metric in app.metric if metric.label == "Marcha") == "3"
    next(button for button in app.button if button.label == "Reiniciar").click().run()
    assert app.session_state["driving_playback"].position == 0.0
    assert not app.exception
