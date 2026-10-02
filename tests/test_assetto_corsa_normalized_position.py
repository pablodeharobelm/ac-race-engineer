from ctypes import sizeof

import pytest

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
        pass


def test_windows_backend_reads_normalized_car_position() -> None:
    physics = ACPhysicsPage()
    graphics = ACGraphicsPage()
    static = ACStaticPage()

    graphics.normalizedCarPosition = 0.42

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

    def factory(
        size: int,
        name: str,
    ) -> BufferMapping:
        assert len(
            buffers[name]
        ) == size

        return BufferMapping(
            buffers[name]
        )

    backend = WindowsSharedMemoryBackend(
        mapping_factory=factory
    )

    try:
        snapshot = (
            backend.read_graphics()
        )

    finally:
        backend.close()

    assert (
        sizeof(
            ACGraphicsPage
        )
        == len(
            bytes(
                graphics
            )
        )
    )

    assert (
        snapshot.normalized_car_position
        == pytest.approx(
            0.42
        )
    )