from streamlit.testing.v1 import AppTest


def test_signed_steering_chart_and_pedal_modes_render():
    app = AppTest.from_string('''
from ac_race_engineer.dashboard.components import render_trace_comparison
rows = [{"progress": 0, "elapsed_seconds": 0, "speed_kmh": 100, "throttle": 1, "brake": 0, "steering_angle_deg": -30},
        {"progress": 1, "elapsed_seconds": 10, "speed_kmh": 90, "throttle": 0, "brake": 1, "steering_angle_deg": 20}]
render_trace_comparison(rows, rows)
''').run()
    for mode in ("Volante", "Acelerador", "Freno", "Diferencia de tiempo"):
        app.segmented_control[0].set_value(mode).run()
        assert not app.exception
    app.segmented_control[0].set_value("Volante").run()
    assert any("signo registrado" in caption.value for caption in app.caption)
    app.slider[0].set_value((20, 40)).run()
    app.segmented_control[0].set_value("Freno").run()
    assert app.slider[0].value == (20, 40)
    assert any("del 20 % al 40 %" in caption.value for caption in app.caption)
    next(button for button in app.button if button.label == "Ver todo el recorrido").click().run()
    assert app.slider[0].value == (0, 100)
    app.slider[0].set_value((20, 20)).run()
    assert not app.exception
    assert any("Separa el inicio" in item.value for item in app.info)
