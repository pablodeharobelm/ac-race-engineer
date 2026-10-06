from ac_race_engineer.dashboard.report_export import report_html


def test_portable_report_translates_coaching_and_escapes_content():
    report = {"reference_lap_number": 1, "target_lap_number": 2, "net_time_delta_seconds": 0.5,
              "focuses": [{"title": "Improve apex speed", "priority": "high", "corner_number": 1}],
              "corners": [{"corner_number": 1, "time_lost_seconds": 0.5}],
              "explanation": {"language": "es", "text": "<script>alert(1)</script>"}}
    html = report_html(report, {"car_key": "<img src=x>", "track_key": "magione"})
    assert "Mejora la velocidad en el vértice" in html
    assert "Improve apex speed" not in html
    assert "+0.500 s" in html
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;" in html
    assert 'lang="es"' in html
    assert "@media print" in html


def test_historical_reports_and_empty_report_are_supported():
    html = report_html({"report": {"reference_lap_number": 3, "target_lap_number": 4}, "explanation": {"language": "en", "text": "English text"}})
    assert "<strong>3</strong>" in html
    assert "English text" not in html
    assert "No se han detectado" in html
    assert "Sin datos" in report_html({})


def test_report_embeds_sample_coverage_and_offline_charts():
    rows = [{"progress": p, "speed_kmh": v, "throttle": t, "brake": b} for p, v, t, b in
            ((0, 100, 1, 0), (0.5, 60, 0, 0.8), (1, 120, 1, 0))]
    html = report_html({"time_estimated": True}, reference_trace=rows, target_trace=rows)
    assert html.count("<svg ") == 3
    assert "3 muestras" in html
    assert "50.0%" in html
    assert "Tiempos estimados" in html
    assert "#35d78b" in html
    assert "#ff6577" in html
    assert 'stroke-dasharray="7 4"' in html
    assert "<script" not in html
    assert "https://" not in html
