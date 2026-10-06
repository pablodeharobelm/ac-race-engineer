import ast
from pathlib import Path

from ac_race_engineer.dashboard.locale_es import COACHING, api_error_message, format_date
from ac_race_engineer.dashboard.session_visuals import session_image


def test_every_generated_recommendation_has_spanish_copy():
    source = Path(__file__).parents[1] / "src/ac_race_engineer/telemetry/assetto_corsa/trace_driving_recommendations.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    titles = {
        keyword.value.value
        for node in ast.walk(tree) if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "title" and isinstance(keyword.value, ast.Constant)
    }
    assert titles
    assert titles <= COACHING.keys()


def test_session_media_uses_local_game_assets_or_honest_fallback(tmp_path):
    car = tmp_path / "content/cars/ks_mazda_mx5_cup/skins/baseline/preview.jpg"
    track = tmp_path / "content/tracks/magione/map.png"
    car.parent.mkdir(parents=True)
    track.parent.mkdir(parents=True)
    car.write_bytes(b"test asset")
    track.write_bytes(b"test asset")
    assert session_image("car", "ks_mazda_mx5_cup", str(tmp_path)).path == car
    assert session_image("track", "magione", str(tmp_path)).path == track
    assert not session_image("car", "ks_mazda_mx5_cup", str(tmp_path)).provisional
    for kind, key in (("car", "unknown"), ("track", "../outside")):
        image = session_image(kind, key, str(tmp_path))
        assert image.provisional
        assert image.path.is_file()


def test_dates_and_errors_are_readable_in_spanish():
    assert format_date("2026-10-05T14:00:00Z") == "05/10/2026 · 16:00"
    assert format_date("2026-10-05T14:00:00") == "05/10/2026 · 16:00"
    assert format_date("invalid") == "Fecha no disponible"
    assert "IA" in api_error_message(RuntimeError("HTTP 503: LLM explanation service is not configured"))
    assert "vuelta" in api_error_message(RuntimeError("HTTP 409: The driving trace file is missing"))
