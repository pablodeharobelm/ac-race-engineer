import argparse
import sys
from collections.abc import Sequence

from ac_race_engineer.database.session import (
    create_database_engine,
    database_session,
)
from ac_race_engineer.telemetry.assetto_corsa.capture_runner import (
    AssettoCorsaCaptureRunner,
)
from ac_race_engineer.telemetry.assetto_corsa.exceptions import (
    AssettoCorsaReadError,
    AssettoCorsaStaleDataError,
    AssettoCorsaUnavailableError,
)
from ac_race_engineer.telemetry.assetto_corsa.fake import (
    FakeAssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.persistence import (
    AssettoCorsaPersistenceService,
)
from ac_race_engineer.telemetry.assetto_corsa.source import (
    AssettoCorsaSource,
)
from ac_race_engineer.telemetry.assetto_corsa.windows_backend import (
    WindowsSharedMemoryBackend,
)
from ac_race_engineer.telemetry.models import (
    TelemetryFrame,
)


def _positive_int(
    value: str,
) -> int:
    parsed = int(
        value
    )

    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            "value must be greater than 0"
        )

    return parsed


def _non_negative_float(
    value: str,
) -> float:
    parsed = float(
        value
    )

    if parsed < 0.0:
        raise argparse.ArgumentTypeError(
            "value must be greater than or equal to 0"
        )

    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture Assetto Corsa telemetry "
            "and persist session data"
        )
    )

    mode = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    mode.add_argument(
        "--fake",
        action="store_true",
        help=(
            "Use generated Assetto Corsa data "
            "without requiring the game"
        ),
    )

    mode.add_argument(
        "--real",
        action="store_true",
        help=(
            "Read real Assetto Corsa "
            "shared memory"
        ),
    )

    parser.add_argument(
        "--samples",
        type=_positive_int,
        default=None,
        help=(
            "Number of frames to capture. "
            "If omitted, capture continues "
            "until Ctrl+C."
        ),
    )

    parser.add_argument(
        "--interval",
        type=_non_negative_float,
        default=0.05,
        help=(
            "Seconds between telemetry reads "
            "(default: 0.05 = approximately 20 Hz)"
        ),
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Do not print every telemetry frame"
        ),
    )

    return parser


def _print_frame(
    frame: TelemetryFrame,
) -> None:
    vehicle = (
        frame.vehicle
    )

    print(
        f"[{frame.sample_index:06d}] "
        f"{frame.car_id} @ {frame.track_id} | "
        f"{vehicle.speed_kmh:6.1f} km/h | "
        f"{vehicle.rpm:5d} rpm | "
        f"gear={vehicle.gear:2d} | "
        f"gas={vehicle.throttle:.2f} | "
        f"brake={vehicle.brake:.2f}"
    )


def _print_summary(
    *,
    frames: int,
    sessions: int,
    laps: int,
    sectors: int,
    traces: int,
) -> None:
    print()

    print(
        "=" * 60
    )

    print(
        "Assetto Corsa capture summary"
    )

    print(
        "=" * 60
    )

    print(
        f"Frames read:       {frames}"
    )

    print(
        f"Sessions saved:    {sessions}"
    )

    print(
        f"Laps saved:        {laps}"
    )

    print(
        f"Sectors saved:     {sectors}"
    )

    print(
        f"Lap traces saved:  {traces}"
    )


def _run_fake(
    *,
    samples: int | None,
    interval: float,
    quiet: bool,
) -> int:
    backend = (
        FakeAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend,
        stale_timeout_seconds=None,
    )

    return _run_capture(
        source=source,
        samples=samples,
        interval=interval,
        quiet=quiet,
    )


def _run_real(
    *,
    samples: int | None,
    interval: float,
    quiet: bool,
) -> int:
    try:
        with (
            WindowsSharedMemoryBackend()
            as backend
        ):
            source = (
                AssettoCorsaSource(
                    backend,
                    stale_timeout_seconds=2.0,
                )
            )

            print(
                "Connected to Assetto Corsa "
                "shared memory."
            )

            return _run_capture(
                source=source,
                samples=samples,
                interval=interval,
                quiet=quiet,
            )

    except AssettoCorsaUnavailableError as exc:
        print(
            "Assetto Corsa shared memory "
            "is not available.",
            file=sys.stderr,
        )

        print(
            str(
                exc
            ),
            file=sys.stderr,
        )

        print(
            "Start Assetto Corsa and enter "
            "an on-track session first.",
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
            str(
                exc
            ),
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
            str(
                exc
            ),
            file=sys.stderr,
        )

        return 4


def _run_capture(
    *,
    source: AssettoCorsaSource,
    samples: int | None,
    interval: float,
    quiet: bool,
) -> int:
    engine = (
        create_database_engine()
    )

    frames_read = 0
    sessions_saved = 0
    laps_saved = 0
    sectors_saved = 0
    traces_saved = 0

    try:
        with database_session(
            engine
        ) as session:
            persistence = (
                AssettoCorsaPersistenceService(
                    session
                )
            )

            runner = (
                AssettoCorsaCaptureRunner(
                    source=source,
                    persistence=persistence,
                )
            )

            callback = (
                None
                if quiet
                else _print_frame
            )

            try:
                result = runner.run(
                    samples=samples,
                    interval_seconds=interval,
                    on_frame=callback,
                )

                frames_read += (
                    result.frames_read
                )

                sessions_saved += (
                    result.sessions_saved
                )

                laps_saved += (
                    result.laps_saved
                )

                sectors_saved += (
                    result.sectors_saved
                )

                traces_saved += (
                    result.traces_saved
                )

            except KeyboardInterrupt:
                print()

                print(
                    "Capture stopped by user."
                )

                (
                    final_sessions,
                    final_laps,
                    final_sectors,
                    final_traces,
                ) = runner.finish()

                sessions_saved += (
                    final_sessions
                )

                laps_saved += (
                    final_laps
                )

                sectors_saved += (
                    final_sectors
                )

                traces_saved += (
                    final_traces
                )

    finally:
        engine.dispose()

    _print_summary(
        frames=frames_read,
        sessions=sessions_saved,
        laps=laps_saved,
        sectors=sectors_saved,
        traces=traces_saved,
    )

    return 0


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = (
        _build_parser()
    )

    args = (
        parser.parse_args(
            argv
        )
    )

    print(
        "AC Race Engineer - "
        "Assetto Corsa Capture"
    )

    print(
        "-" * 60
    )

    if args.fake:
        print(
            "Mode: FAKE"
        )

        return _run_fake(
            samples=args.samples,
            interval=args.interval,
            quiet=args.quiet,
        )

    print(
        "Mode: REAL"
    )

    return _run_real(
        samples=args.samples,
        interval=args.interval,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )