from ac_race_engineer.domain.setup import CarSetup
from ac_race_engineer.services.parameter_sweep import (
    ParameterSweepRunner,
)


def main():

    baseline = CarSetup(
        car_id="mazda_mx5_cup",
        name="Development baseline",
        values={
            "front_pressure": 24.5,
            "rear_pressure": 24.5,
            "front_camber": -2.5,
            "rear_camber": -2.0,
            "brake_bias": 0.64,
        },
    )

    runner = ParameterSweepRunner()

    result = runner.run(
        baseline_setup=baseline,
        parameter="front_pressure",
        values=[
            23.0,
            23.5,
            24.0,
            24.5,
            25.0,
            25.5,
            26.0,
        ],
        seed=42,
        hz=20,
        sample_count=1200,
    )

    print()
    print("PARAMETER SWEEP")
    print("================")
    print()

    print(
        f"Parameter: {result.parameter}"
    )

    print(
        f"Baseline: {result.baseline_value}"
    )

    print()

    for point in result.points:

        print(
            f"{point.parameter_value:5.1f} PSI | "
            f"Pressure: "
            f"{point.front_pressure_psi:5.2f} | "
            f"Temp: "
            f"{point.front_core_temperature_c:5.1f} C | "
            f"Slip: "
            f"{point.front_slip_angle_deg:5.2f} deg"
        )


if __name__ == "__main__":
    main()