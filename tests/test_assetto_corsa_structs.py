from ctypes import sizeof

import pytest

from ac_race_engineer.telemetry.assetto_corsa.structs import (
    ACGraphicsPage,
    ACPhysicsPage,
    ACStaticPage,
    Utf16_33,
    decode_utf16,
)


def test_assetto_corsa_structs_use_pack_4() -> None:
    assert ACPhysicsPage._pack_ == 4
    assert ACGraphicsPage._pack_ == 4
    assert ACStaticPage._pack_ == 4


def test_assetto_corsa_structs_have_data() -> None:
    assert sizeof(ACPhysicsPage) > 0
    assert sizeof(ACGraphicsPage) > 0
    assert sizeof(ACStaticPage) > 0


def test_physics_binary_round_trip() -> None:
    original = ACPhysicsPage()

    original.packetId = 42
    original.gas = 0.75
    original.rpms = 6500
    original.speedKmh = 142.5

    original.wheelsPressure[0] = 26.1

    payload = bytes(
        original
    )

    restored = (
        ACPhysicsPage.from_buffer_copy(
            payload
        )
    )

    assert restored.packetId == 42

    assert restored.gas == pytest.approx(
        0.75
    )

    assert restored.rpms == 6500

    assert restored.speedKmh == pytest.approx(
        142.5
    )

    assert (
        restored.wheelsPressure[0]
        == pytest.approx(26.1)
    )


def test_decode_utf16() -> None:
    value = Utf16_33()

    text = "ks_mazda_mx5_cup"

    for index, character in enumerate(
        text
    ):
        value[index] = ord(
            character
        )

    assert decode_utf16(
        value
    ) == text