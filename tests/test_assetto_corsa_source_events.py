from dataclasses import replace

from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)


class EventBackend(
    FakeAssettoCorsaBackend
):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self.graphics_override = None

    def read_graphics(
        self,
    ):
        original = (
            super().read_graphics()
        )

        if self.graphics_override is None:
            return original

        return replace(
            self.graphics_override,
            packet_id=self.packet_id,
        )


def test_no_events_initially() -> None:
    source = AssettoCorsaSource(
        EventBackend()
    )

    source.read_frame()

    assert (
        source.last_lap_event
        is None
    )

    assert (
        source.last_sector_event
        is None
    )

    assert (
        source.lap_events_pending
        == 0
    )

    assert (
        source.sector_events_pending
        == 0
    )


def test_source_queues_lap_event() -> None:
    backend = EventBackend()

    source = AssettoCorsaSource(
        backend
    )

    source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        completed_laps=(
            graphics.completed_laps + 1
        ),
        last_time_ms=104532,
        best_time_ms=104532,
    )

    frame = source.read_frame()

    assert (
        source.lap_events_pending
        == 1
    )

    event = (
        source.pop_lap_event()
    )

    assert event is not None

    assert (
        event.session_id
        == frame.session_id
    )

    assert (
        event.lap_time_ms
        == 104532
    )

    assert event.is_best

    assert (
        source.lap_events_pending
        == 0
    )


def test_source_queues_sector_event() -> None:
    backend = EventBackend()

    source = AssettoCorsaSource(
        backend
    )

    source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        current_sector_index=(
            graphics.current_sector_index + 1
        ),
        last_sector_time_ms=33184,
    )

    frame = source.read_frame()

    assert (
        source.sector_events_pending
        == 1
    )

    event = (
        source.pop_sector_event()
    )

    assert event is not None

    assert (
        event.session_id
        == frame.session_id
    )

    assert (
        event.sector_time_ms
        == 33184
    )


def test_lap_crossing_can_emit_lap_and_sector() -> None:
    backend = EventBackend()

    source = AssettoCorsaSource(
        backend
    )

    source.read_frame()

    graphics = (
        backend.read_graphics()
    )

    backend.graphics_override = replace(
        graphics,
        completed_laps=(
            graphics.completed_laps + 1
        ),
        current_sector_index=0,
        last_time_ms=104500,
        best_time_ms=104500,
        last_sector_time_ms=34000,
    )

    source.read_frame()

    assert (
        source.lap_events_pending
        == 1
    )

    assert (
        source.sector_events_pending
        == 1
    )


def test_event_pop_returns_none_when_empty() -> None:
    source = AssettoCorsaSource(
        EventBackend()
    )

    assert (
        source.pop_lap_event()
        is None
    )

    assert (
        source.pop_sector_event()
        is None
    )