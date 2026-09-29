import argparse
import sys
import time
from collections.abc import Sequence

from ac_race_engineer.telemetry.assetto_corsa import (
    AssettoCorsaReadError,
    AssettoCorsaSource,
    AssettoCorsaStaleDataError,
    AssettoCorsaUnavailableError,
    FakeAssettoCorsaBackend,
    WindowsSharedMemoryBackend,
)
from ac_race_engineer.telemetry.models import TelemetryFrame


def _positive_int(
    value: str,
) -> int:
    parsed = int(value)

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be greater than 0"
        )

    return parsed


def _non_negative_float(
    value: str,
) -> float:
    parsed = float(value)

    if parsed < 0.0:
        raise argparse.ArgumentTypeError(
            "value must be greater than or equal to 0"
        )

    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Assetto Corsa telemetry smoke test"
        )
    )

    mode = parser.add_mutually_exclusive_group(
        required=True
    )

    mode.add_argument(
        "--fake",
        action="store_true",
        help=(
            "Use fake Assetto Corsa telemetry "
            "without requiring the game"
        ),
    )

    mode.add_argument(
        "--real",
        action="store_true",
        help=(
            "Read Assetto Corsa Windows "
            "shared memory"
        ),
    )

    parser.add_argument(
        "--samples",
        type=_positive_int,
        default=10,
        help="Number of telemetry frames to read",
    )

    parser.add_argument(
        "--interval",
        type=_non_negative_float,
        default=0.1,
        help=(
            "Seconds to wait between samples"
        ),
    )

    return parser


def _print_frame(
    frame: TelemetryFrame,
) -> None:
    vehicle = frame.vehicle

    print(
        f"[{frame.sample_index:04d}] "
        f"car={frame.car_id} "
        f"track={frame.track_id} "
        f"speed={vehicle.speed_kmh:.1f}km/h "
        f"rpm={vehicle.rpm} "
        f"gear={vehicle.gear} "
        f"gas={vehicle.throttle:.2f} "
        f"brake={vehicle.brake:.2f}"
    )

    print(
        "       "
        f"FL={frame.wheels['FL'].pressure_psi:.1f}psi "
        f"FR={frame.wheels['FR'].pressure_psi:.1f}psi "
        f"RL={frame.wheels['RL'].pressure_psi:.1f}psi "
        f"RR={frame.wheels['RR'].pressure_psi:.1f}psi"
    )


def _run_source(
    source: AssettoCorsaSource,
    *,
    samples: int,
    interval: float,
) -> None:
    print(
        f"source={source.source_name}"
    )

    print(
        f"session_id={source.session_id}"
    )

    print("-" * 80)

    for index in range(samples):
        frame = source.read_frame()

        _print_frame(
            frame
        )

        if (
            interval > 0.0
            and index < samples - 1
        ):
            time.sleep(
                interval
            )


def _run_fake(
    *,
    samples: int,
    interval: float,
) -> int:
    backend = FakeAssettoCorsaBackend()

    source = AssettoCorsaSource(
        backend,
    )

    print(
        "Assetto Corsa smoke test: FAKE MODE"
    )

    _run_source(
        source,
        samples=samples,
        interval=interval,
    )

    return 0


def _run_real(
    *,
    samples: int,
    interval: float,
) -> int:
    print(
        "Assetto Corsa smoke test: REAL MODE"
    )

    print(
        "Connecting to Assetto Corsa "
        "shared memory..."
    )

    try:
        with WindowsSharedMemoryBackend() as backend:
            source = AssettoCorsaSource(
                backend,
                stale_timeout_seconds=2.0,
            )

            print(
                "Shared memory connected."
            )

            _run_source(
                source,
                samples=samples,
                interval=interval,
            )

    except AssettoCorsaUnavailableError as exc:
        print(
            "Assetto Corsa shared memory "
            "is not available.",
            file=sys.stderr,
        )

        print(
            str(exc),
            file=sys.stderr,
        )

        print(
            "Start Assetto Corsa and enter "
            "an on-track session before "
            "running --real.",
            file=sys.stderr,
        )

        return 2

    except AssettoCorsaStaleDataError as exc:
        print(
            "Assetto Corsa telemetry "
            "stopped updating.",
            file=sys.stderr,
        )

        print(
            str(exc),
            file=sys.stderr,
        )

        return 3

    except AssettoCorsaReadError as exc:
        print(
            "Failed to read Assetto Corsa "
            "shared memory.",
            file=sys.stderr,
        )

        print(
            str(exc),
            file=sys.stderr,
        )

        return 4

    return 0


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = _build_parser()

    args = parser.parse_args(
        argv
    )

    if args.fake:
        return _run_fake(
            samples=args.samples,
            interval=args.interval,
        )

    return _run_real(
        samples=args.samples,
        interval=args.interval,
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )