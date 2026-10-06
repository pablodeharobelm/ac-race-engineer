from dataclasses import replace

from ac_race_engineer.telemetry.assetto_corsa.exceptions import AssettoCorsaUnavailableError
from ac_race_engineer.telemetry.assetto_corsa.fake import FakeAssettoCorsaBackend
from ac_race_engineer.telemetry.assetto_corsa.live_monitor import LiveMonitor


class Backend(FakeAssettoCorsaBackend):
    status = 2
    packet = 1
    closed = False

    def read_physics(self):
        return replace(super().read_physics(), packet_id=self.packet)

    def read_graphics(self):
        return replace(super().read_graphics(), status=self.status)

    def close(self):
        self.closed = True


def test_waiting_retry_disconnect_and_recovery():
    now = [0.0]
    available = [False]
    instances = []
    def factory():
        if not available[0]:
            raise AssettoCorsaUnavailableError()
        backend = Backend()
        instances.append(backend)
        return backend
    monitor = LiveMonitor(factory, clock=lambda: now[0])
    assert monitor.poll().state == "waiting"
    available[0] = True
    now[0] = 1
    assert monitor.poll().state == "waiting"
    now[0] = 2
    assert monitor.poll().state == "live"
    now[0] = 5
    assert monitor.poll().state == "disconnected"
    assert instances[0].closed
    assert monitor.poll().physics is None
    now[0] = 7
    assert monitor.poll().state == "live"
    monitor.close()
    assert instances[-1].closed


def test_pause_is_not_a_stale_packet_failure_and_offline_clears_data():
    now = [0.0]
    backend = Backend()
    monitor = LiveMonitor(lambda: backend, clock=lambda: now[0])
    assert monitor.poll().state == "live"
    backend.status = 3
    now[0] = 50
    assert monitor.poll().state == "paused"
    backend.status = 0
    assert monitor.poll().state == "waiting"
    assert backend.closed


def test_game_replay_is_explicit():
    backend = Backend()
    backend.status = 1
    monitor = LiveMonitor(lambda: backend)
    assert monitor.poll().state == "replay"


def test_resuming_from_pause_has_time_to_receive_a_new_packet():
    now = [0.0]
    backend = Backend()
    monitor = LiveMonitor(lambda: backend, clock=lambda: now[0])
    assert monitor.poll().state == "live"
    backend.status = 3
    now[0] = 50
    assert monitor.poll().state == "paused"
    backend.status = 2
    now[0] = 50.25
    assert monitor.poll().state == "live"
    backend.packet += 1
    now[0] = 51
    assert monitor.poll().state == "live"


def test_unknown_game_status_never_displays_live_values():
    backend = Backend()
    backend.status = 99
    reading = LiveMonitor(lambda: backend).poll()
    assert reading.state == "disconnected"
    assert reading.physics is None
