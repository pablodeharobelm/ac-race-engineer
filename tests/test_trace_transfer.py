import json

import pytest

from ac_race_engineer.dashboard.app import DEFAULT_REFERENCE_TRACE, _parse_trace
from ac_race_engineer.dashboard.trace_transfer import (
    distance_extent,
    ensure_same_context,
    needs_estimated_time,
    trace_file,
)


def test_lap_export_import_roundtrip():
    samples = [dict(sample, gear=3, clutch=0.4) for sample in DEFAULT_REFERENCE_TRACE]
    exported = trace_file(samples, lap_number=4, session={"car_key": "mazda", "track_key": "magione"})
    assert json.loads(exported)["lap_number"] == 4
    assert _parse_trace(exported, label="la vuelta") == samples
    assert _parse_trace(json.dumps(samples), label="la vuelta") == samples


def test_unsupported_versions_and_missing_samples_are_clear():
    with pytest.raises(ValueError, match="versión"):
        _parse_trace('{"format":"ac-race-engineer-lap","version":2,"samples":[]}', label="la vuelta")
    with pytest.raises(TypeError, match="lista"):
        _parse_trace('{}', label="la vuelta")


def test_two_exported_laps_must_match_car_and_track():
    reference = trace_file(DEFAULT_REFERENCE_TRACE, lap_number=1, session={"car_key": "car-a", "track_key": "magione"})
    target = trace_file(DEFAULT_REFERENCE_TRACE, lap_number=2, session={"car_key": "car-b", "track_key": "magione"})
    with pytest.raises(ValueError, match="coche"):
        ensure_same_context(reference, target)
    ensure_same_context(reference, reference)


def test_import_rejects_nonfinite_and_missing_telemetry_locally():
    samples = [dict(sample) for sample in DEFAULT_REFERENCE_TRACE]
    samples[0]["speed_kmh"] = float("nan")
    with pytest.raises(ValueError, match="muestra 1"):
        _parse_trace(json.dumps(samples), label="la vuelta")
    samples[0] = {"progress": 0}
    with pytest.raises(ValueError, match="incompletos"):
        _parse_trace(json.dumps(samples), label="la vuelta")


def test_distance_percentages_and_named_track_wrapper():
    rows = [{"lap_distance_m": distance, "speed_kmh": 36, "throttle_pct": 50, "brake_pct": 20, "steering_deg": 4, "gear": 2} for distance in (0, 100)]
    text = json.dumps({"magione": rows})
    with pytest.raises(ValueError, match="no incluyen tiempos"):
        _parse_trace(text, label="la vuelta")
    converted = _parse_trace(text, label="la vuelta", allow_estimated_time=True, track_length=120)
    assert converted[-1]["elapsed_seconds"] == pytest.approx(10)
    assert converted[-1]["progress"] == pytest.approx(100 / 120)
    assert converted[0]["throttle"] == 0.5
    assert converted[0]["brake"] == 0.2
    assert converted[0]["gear"] == 2


def test_distance_rows_preserve_recorded_times():
    rows = [{"lap_distance_m": d, "elapsed_seconds": t, "speed_kmh": 36, "throttle": 1, "brake": 0, "steering_angle_deg": 0} for d, t in ((0, 0), (100, 11))]
    assert _parse_trace(json.dumps(rows), label="la vuelta")[-1]["elapsed_seconds"] == 11
    rows[0]["speed_kmh"] = 0
    assert _parse_trace(json.dumps(rows), label="la vuelta", allow_estimated_time=True)[-1]["elapsed_seconds"] == 11
    assert not needs_estimated_time(json.dumps(rows))
    del rows[1]["elapsed_seconds"]
    assert needs_estimated_time(json.dumps(rows))


def test_distance_extent_uses_common_scale_and_friendly_errors():
    assert distance_extent('[{"lap_distance_m":100}]', '[{"lap_distance_m":120}]') == 120
    with pytest.raises(ValueError, match="JSON válido"):
        distance_extent('{')
    with pytest.raises(ValueError, match="distancias"):
        distance_extent('[{"lap_distance_m":"100"}]')
