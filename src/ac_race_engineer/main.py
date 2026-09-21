from ac_race_engineer.analysis.brake_analyzer import BrakeAnalyzer
from ac_race_engineer.analysis.session_analyzer import (
    SessionAnalyzer,
)
from ac_race_engineer.analysis.tyre_analyzer import TyreAnalyzer
from ac_race_engineer.storage.recorder import (
    SessionRecorder,
)
from ac_race_engineer.telemetry.simulator import (
    SimulatorSource,
)


def main():

    hz = 20
    duration_seconds = 60

    simulator = SimulatorSource(
        hz=hz,
    )

    recorder = SessionRecorder(
        source=simulator,
    )

    sample_count = (
        hz
        * duration_seconds
    )

    output_file = recorder.record_samples(
        sample_count=sample_count,
    )

    analyzer = SessionAnalyzer()

    summary = analyzer.analyze(
        session_file=output_file,
    )

    print()
    print("SESSION ANALYSIS")
    print("================")
    print()

    print(f"Car: {summary.car_id}")
    print(f"Track: {summary.track_id}")

    print(
        f"Duration: "
        f"{summary.duration_seconds:.2f} s"
    )

    print(
        f"Samples: "
        f"{summary.sample_count}"
    )

    print()
    print("VEHICLE")
    print("-------")

    print(
        f"Maximum speed: "
        f"{summary.maximum_speed_kmh:.1f} km/h"
    )

    print(
        f"Maximum lateral G: "
        f"{summary.maximum_lateral_g:.2f} G"
    )

    print(
        f"Maximum braking G: "
        f"{summary.maximum_braking_g:.2f} G"
    )

    print(
        f"Fuel used: "
        f"{summary.fuel_used_l:.3f} L"
    )

    print()
    print("WHEELS")
    print("------")

    for position, wheel in summary.wheels.items():

        print()

        print(position)

        print(
            f"  Avg pressure: "
            f"{wheel.average_pressure_psi:.2f} PSI"
        )

        print(
            f"  Avg tyre temp: "
            f"{wheel.average_core_temp_c:.1f} C"
        )

        print(
            f"  Max tyre temp: "
            f"{wheel.maximum_core_temp_c:.1f} C"
        )

        print(
            f"  Max brake temp: "
            f"{wheel.maximum_brake_temp_c:.1f} C"
        )

        print(
            f"  Max suspension travel: "
            f"{wheel.maximum_suspension_travel_mm:.1f} mm"
        )

    tyre_analyzer = TyreAnalyzer()

    tyre_report = tyre_analyzer.analyze(
        output_file
    )

    print()
    print("TYRE ENGINEERING")
    print("================")

    for position, tyre in tyre_report.wheels.items():

        print()
        print(position)

        print(
            f"  Pressure: "
            f"{tyre.starting_pressure_psi:.2f}"
            f" -> "
            f"{tyre.ending_pressure_psi:.2f} PSI"
        )

        print(
            f"  Pressure gain: "
            f"{tyre.pressure_gain_psi:+.2f} PSI"
        )

        print(
            f"  Temperatures I/M/O: "
            f"{tyre.average_inner_temp_c:.1f} / "
            f"{tyre.average_middle_temp_c:.1f} / "
            f"{tyre.average_outer_temp_c:.1f} C"
        )

        print(
            f"  Inner/outer delta: "
            f"{tyre.inner_outer_delta_c:+.1f} C"
        )

        print(
            f"  Peak core temp: "
            f"{tyre.peak_core_temp_c:.1f} C"
        )

    brake_analyzer = BrakeAnalyzer()

    brake_report = brake_analyzer.analyze(
        output_file
    )

    print()
    print("BRAKE ENGINEERING")
    print("=================")

    print(
        f"Braking events: "
        f"{brake_report.braking_event_count}"
    )

    print(
        f"Maximum brake input: "
        f"{brake_report.maximum_brake_input:.2f}"
    )

    print(
        f"Average brake input: "
        f"{brake_report.average_brake_input_during_events:.2f}"
    )

    print(
        f"Average event duration: "
        f"{brake_report.average_braking_event_duration_seconds:.2f} s"
    )

    print()

    print(
        f"Front brake temperature: "
        f"{brake_report.average_front_temperature_c:.1f} C"
    )

    print(
        f"Rear brake temperature: "
        f"{brake_report.average_rear_temperature_c:.1f} C"
    )

    print(
        f"Front/rear delta: "
        f"{brake_report.front_rear_temperature_delta_c:+.1f} C"
    )

    for position, brake in brake_report.wheels.items():

        print()

        print(position)

        print(
            f"  Avg temperature: "
            f"{brake.average_temperature_c:.1f} C"
        )

        print(
            f"  Peak temperature: "
            f"{brake.peak_temperature_c:.1f} C"
        )

        print(
            f"  Temperature change: "
            f"{brake.temperature_gain_c:+.1f} C"
        )


if __name__ == "__main__":
    main()