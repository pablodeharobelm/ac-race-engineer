import pytest

from ac_race_engineer.dashboard.driving import demo_laps
from ac_race_engineer.dashboard.live_driving import live_delta


def test_reference_comparison_same_position_and_context():
    reference, target = demo_laps()
    assert live_delta(1, target[-1].elapsed_seconds, reference)[0] > 0.9
    assert live_delta(0.5, 20, reference)[0] < 0
    assert live_delta(1, reference[-1].elapsed_seconds, reference)[0] == pytest.approx(0)
    assert live_delta(0.5, 20, reference, compatible=False)[0] is None


def test_reference_never_extrapolates_missing_sections():
    reference = demo_laps()[0][20:100]
    assert live_delta(0, 0, reference)[0] is None
    assert live_delta(1, 60, reference)[0] is None
    assert live_delta(0.2, 20, reference)[0] is not None
    assert live_delta(0.2, 20, ())[0] is None


def test_simulated_clock_does_not_jump_after_pause_or_disconnect():
    from ac_race_engineer.dashboard.live_driving import SimulationClock
    clock = SimulationClock()
    assert clock.advance(0, running=True, duration=60) == 0
    assert clock.advance(10, running=True, duration=60) == 10
    assert clock.advance(50, running=False, duration=60) == 10
    assert clock.advance(100, running=True, duration=60) == 10
    assert clock.advance(103, running=True, duration=60) == 13
