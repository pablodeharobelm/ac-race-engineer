from ctypes import sizeof

import pytest

from ac_race_engineer.telemetry.assetto_corsa.exceptions import (
    AssettoCorsaReadError,
    AssettoCorsaUnavailableError,
)
from ac_race_engineer.telemetry.assetto_corsa.structs import (
    ACGraphicsPage,
    ACPhysicsPage,
    ACStaticPage,
)
from ac_race_engineer.telemetry.assetto_corsa.windows_backend import (
    GRAPHICS_MAPPING,
    PHYSICS_MAPPING,
    STATIC_MAPPING,
    WindowsSharedMemoryBackend,
)


class BufferMapping:
    def __init__(
        self,
        data: bytes,
    ) -> None:
        self.data = data
        self.position = 0
        self.closed = False

    def seek(
        self,
        offset: int,
    ) -> int:
        self.position = offset
        return offset

    def read(
        self,
        size: int,
    ) -> bytes:
        result = self.data[
            self.position:
            self.position + size
        ]

        self.position += len(
            result
        )

        return result

    def close(
        self,
    ) -> None:
        self.closed = True


def set_utf16(
    target: object,
    value: str,
) -> None:
    for index, character in enumerate(
        value
    ):
        target[index] = ord(
            character
        )


def build_physics() -> ACPhysicsPage:
    page = ACPhysicsPage()

    page.packetId = 123
    page.gas = 0.82
    page.brake = 0.15
    page.clutch = 0.0

    page.fuel = 31.5

    page.gear = 4
    page.rpms = 6125

    page.steerAngle = 0.08
    page.speedKmh = 143.2

    page.accG[0] = 0.72
    page.accG[2] = 0.18

    pressures = (
        26.1,
        26.0,
        25.8,
        25.9,
    )

    for index, pressure in enumerate(
        pressures
    ):
        page.wheelsPressure[
            index
        ] = pressure

        page.wheelSlip[
            index
        ] = 0.03 + index * 0.01

        page.wheelLoad[
            index
        ] = 3000.0 + index * 100.0

        page.wheelAngularSpeed[
            index
        ] = 112.0 + index

        page.tyreCoreTemperature[
            index
        ] = 80.0 + index

        page.tyreTempI[
            index
        ] = 84.0 + index

        page.tyreTempM[
            index
        ] = 80.0 + index

        page.tyreTempO[
            index
        ] = 76.0 + index

        page.brakeTemp[
            index
        ] = 400.0 + index * 10.0

        page.suspensionTravel[
            index
        ] = 0.05 + index * 0.001

    page.brakeBias = 0.64

    page.pitch = -0.01
    page.roll = 0.02

    page.rideHeight[0] = 0.068
    page.rideHeight[1] = 0.074

    page.airTemp = 24.0
    page.roadTemp = 31.0

    return page


def build_graphics() -> ACGraphicsPage:
    page = ACGraphicsPage()

    page.packetId = 321
    page.status = 2
    page.session = 0

    page.completedLaps = 3
    page.position = 2

    page.sessionTimeLeft = 1200.0
    page.distanceTraveled = 8400.0

    page.currentSectorIndex = 1

    page.surfaceGrip = 0.98

    return page


def build_static() -> ACStaticPage:
    page = ACStaticPage()

    set_utf16(
        page.carModel,
        "ks_mazda_mx5_cup",
    )

    set_utf16(
        page.track,
        "magione",
    )

    page.maxRpm = 7500
    page.maxFuel = 45.0

    for index in range(4):
        page.tyreRadius[
            index
        ] = 0.31

    return page


def test_windows_backend_reads_snapshots() -> None:
    physics = build_physics()
    graphics = build_graphics()
    static = build_static()

    buffers = {
        PHYSICS_MAPPING: bytes(
            physics
        ),
        GRAPHICS_MAPPING: bytes(
            graphics
        ),
        STATIC_MAPPING: bytes(
            static
        ),
    }

    mappings: dict[
        str,
        BufferMapping,
    ] = {}

    def factory(
        size: int,
        name: str,
    ) -> BufferMapping:
        assert len(
            buffers[name]
        ) == size

        mapping = BufferMapping(
            buffers[name]
        )

        mappings[name] = mapping

        return mapping

    backend = WindowsSharedMemoryBackend(
        mapping_factory=factory
    )

    physics_snapshot = (
        backend.read_physics()
    )

    graphics_snapshot = (
        backend.read_graphics()
    )

    static_snapshot = (
        backend.read_static()
    )

    assert (
        physics_snapshot.packet_id
        == 123
    )

    assert (
        physics_snapshot.speed_kmh
        == pytest.approx(143.2)
    )

    assert (
        physics_snapshot.rpm
        == 6125
    )

    assert (
        physics_snapshot.wheel_pressure_psi[
            0
        ]
        == pytest.approx(26.1)
    )

    assert (
        graphics_snapshot.packet_id
        == 321
    )

    assert (
        graphics_snapshot.completed_laps
        == 3
    )

    assert (
        graphics_snapshot.surface_grip
        == pytest.approx(0.98)
    )

    assert (
        static_snapshot.car_model
        == "ks_mazda_mx5_cup"
    )

    assert (
        static_snapshot.track
        == "magione"
    )

    assert (
        static_snapshot.max_rpm
        == 7500
    )

    assert (
        static_snapshot.tyre_radius_m[
            0
        ]
        == pytest.approx(0.31)
    )

    backend.close()

    assert all(
        mapping.closed
        for mapping in mappings.values()
    )


def test_struct_sizes_match_test_buffers() -> None:
    assert (
        len(bytes(build_physics()))
        == sizeof(ACPhysicsPage)
    )

    assert (
        len(bytes(build_graphics()))
        == sizeof(ACGraphicsPage)
    )

    assert (
        len(bytes(build_static()))
        == sizeof(ACStaticPage)
    )

def test_backend_reports_unavailable_memory() -> None:
    def unavailable_factory(
        size: int,
        name: str,
    ) -> BufferMapping:
        raise AssettoCorsaUnavailableError(
            f"Unavailable: {name}"
        )

    with pytest.raises(
        AssettoCorsaUnavailableError,
        match="Unavailable",
    ):
        WindowsSharedMemoryBackend(
            mapping_factory=unavailable_factory
        )


def test_backend_closes_partial_initialization() -> None:
    physics = build_physics()

    first_mapping = BufferMapping(
        bytes(physics)
    )

    calls = 0

    def factory(
        size: int,
        name: str,
    ) -> BufferMapping:
        nonlocal calls

        calls += 1

        if calls == 1:
            return first_mapping

        raise AssettoCorsaUnavailableError(
            f"Unavailable: {name}"
        )

    with pytest.raises(
        AssettoCorsaUnavailableError
    ):
        WindowsSharedMemoryBackend(
            mapping_factory=factory
        )

    assert first_mapping.closed


def test_read_after_close_fails_cleanly() -> None:
    buffers = {
        PHYSICS_MAPPING: bytes(
            build_physics()
        ),
        GRAPHICS_MAPPING: bytes(
            build_graphics()
        ),
        STATIC_MAPPING: bytes(
            build_static()
        ),
    }

    def factory(
        size: int,
        name: str,
    ) -> BufferMapping:
        return BufferMapping(
            buffers[name]
        )

    backend = WindowsSharedMemoryBackend(
        mapping_factory=factory
    )

    backend.close()

    with pytest.raises(
        AssettoCorsaReadError,
        match="closed",
    ):
        backend.read_physics()


def test_short_shared_memory_read_fails() -> None:
    physics = bytes(
        build_physics()
    )

    buffers = {
        PHYSICS_MAPPING: physics[:-10],
        GRAPHICS_MAPPING: bytes(
            build_graphics()
        ),
        STATIC_MAPPING: bytes(
            build_static()
        ),
    }

    def factory(
        size: int,
        name: str,
    ) -> BufferMapping:
        return BufferMapping(
            buffers[name]
        )

    backend = WindowsSharedMemoryBackend(
        mapping_factory=factory
    )

    with pytest.raises(
        AssettoCorsaReadError,
        match="Unexpected shared-memory size",
    ):
        backend.read_physics()

    backend.close()