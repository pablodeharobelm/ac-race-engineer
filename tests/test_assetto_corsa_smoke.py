import pytest

import ac_race_engineer.assetto_corsa_smoke as smoke
from ac_race_engineer.telemetry.assetto_corsa.exceptions import (
    AssettoCorsaUnavailableError,
)


def test_fake_smoke_runs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = smoke.main(
        [
            "--fake",
            "--samples",
            "2",
            "--interval",
            "0",
        ]
    )

    captured = capsys.readouterr()

    assert result == 0

    assert (
        "FAKE MODE"
        in captured.out
    )

    assert (
        "ks_mazda_mx5_cup"
        in captured.out
    )

    assert (
        "magione"
        in captured.out
    )

    assert (
        "[0001]"
        in captured.out
    )

    assert (
        "[0002]"
        in captured.out
    )


def test_fake_smoke_prints_telemetry(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = smoke.main(
        [
            "--fake",
            "--samples",
            "1",
            "--interval",
            "0",
        ]
    )

    captured = capsys.readouterr()

    assert result == 0

    assert (
        "speed=143.2km/h"
        in captured.out
    )

    assert (
        "rpm=6150"
        in captured.out
    )

    assert (
        "gear=3"
        in captured.out
    )

    assert (
        "FL=26.1psi"
        in captured.out
    )


def test_real_smoke_handles_unavailable_ac(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class UnavailableBackend:
        def __init__(
            self,
        ) -> None:
            raise AssettoCorsaUnavailableError(
                "Test shared memory unavailable"
            )

    monkeypatch.setattr(
        smoke,
        "WindowsSharedMemoryBackend",
        UnavailableBackend,
    )

    result = smoke.main(
        [
            "--real",
            "--samples",
            "1",
        ]
    )

    captured = capsys.readouterr()

    assert result == 2

    assert (
        "shared memory is not available"
        in captured.err
    )

    assert (
        "Test shared memory unavailable"
        in captured.err
    )


@pytest.mark.parametrize(
    "samples",
    [
        "0",
        "-1",
    ],
)
def test_rejects_invalid_sample_count(
    samples: str,
) -> None:
    with pytest.raises(
        SystemExit
    ):
        smoke.main(
            [
                "--fake",
                "--samples",
                samples,
            ]
        )


def test_rejects_negative_interval() -> None:
    with pytest.raises(
        SystemExit
    ):
        smoke.main(
            [
                "--fake",
                "--interval",
                "-0.1",
            ]
        )


def test_requires_mode() -> None:
    with pytest.raises(
        SystemExit
    ):
        smoke.main(
            []
        )


def test_fake_and_real_are_mutually_exclusive() -> None:
    with pytest.raises(
        SystemExit
    ):
        smoke.main(
            [
                "--fake",
                "--real",
            ]
        )