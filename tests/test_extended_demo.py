from itertools import pairwise

import pytest

from ac_race_engineer.telemetry.assetto_corsa.demo_backend import DemoAssettoCorsaBackend


def test_practice_has_improvement_and_variable_pace():
    backend = DemoAssettoCorsaBackend(lap_count=6)
    assert backend.sample_count == 1207
    times = [lap[-1].elapsed_seconds for lap in backend.laps]
    assert times[1] > times[0]
    assert times[2] < times[0]
    assert min(times) == times[5]
    assert times[4] > times[3]
    for lap in backend.laps:
        assert all(a.elapsed_seconds < b.elapsed_seconds for a, b in pairwise(lap))


def test_best_time_tracks_completed_laps():
    backend = DemoAssettoCorsaBackend(lap_count=6)
    for _ in range(backend.sample_count):
        backend.read_physics()
        graphics = backend.read_graphics()
    assert graphics.completed_laps == 6
    assert graphics.best_time_ms == round(min(lap[-1].elapsed_seconds for lap in backend.laps) * 1000)


@pytest.mark.parametrize("count", [0, 1, 21])
def test_demo_rejects_unbounded_sessions(count):
    with pytest.raises(ValueError):
        DemoAssettoCorsaBackend(lap_count=count)
