from ac_race_engineer.telemetry.assetto_corsa import (
    AssettoCorsaSource,
    FakeAssettoCorsaBackend,
)


def main() -> None:
    backend = (
        FakeAssettoCorsaBackend()
    )

    source = AssettoCorsaSource(
        backend
    )

    for _ in range(5):
        frame = (
            source.read_frame()
        )

        print(
            "SESSION:",
            frame.session_id,
        )

        print(
            "SAMPLE:",
            frame.sample_index,
        )

        print(
            "CAR:",
            frame.car_id,
        )

        print(
            "TRACK:",
            frame.track_id,
        )

        print(
            "SPEED:",
            round(
                frame.vehicle.speed_kmh,
                1,
            ),
            "km/h",
        )

        print(
            "RPM:",
            frame.vehicle.rpm,
        )

        print(
            "GEAR:",
            frame.vehicle.gear,
        )

        print(
            "THROTTLE:",
            frame.vehicle.throttle,
        )

        print(
            "BRAKE:",
            frame.vehicle.brake,
        )

        print(
            "FL PRESSURE:",
            frame.wheels[
                "FL"
            ].pressure_psi,
        )

        print("-" * 40)


if __name__ == "__main__":
    main()