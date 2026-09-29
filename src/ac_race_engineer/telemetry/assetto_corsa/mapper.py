from datetime import datetime
from math import degrees

from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
    ACPhysicsSnapshot,
    ACStaticSnapshot,
)
from ac_race_engineer.telemetry.models import (
    EnvironmentTelemetry,
    TelemetryFrame,
    VehicleTelemetry,
    WheelTelemetry,
)

WHEEL_ORDER = (
    "FL",
    "FR",
    "RL",
    "RR",
)


def normalize_gear(
    raw_gear: int,
) -> int:
    """
    Convert Assetto Corsa gear representation to the
    representation used by the application.

    -1 = reverse
     0 = neutral
     1+ = forward gears
    """

    if raw_gear == 0:
        return -1

    if raw_gear == 1:
        return 0

    return raw_gear - 1


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def map_assetto_corsa_frame(
    *,
    physics: ACPhysicsSnapshot,
    graphics: ACGraphicsSnapshot,
    static: ACStaticSnapshot,
    timestamp: datetime,
    session_id: str,
    sample_index: int,
    elapsed_seconds: float,
) -> TelemetryFrame:

    wheels: dict[
        str,
        WheelTelemetry,
    ] = {}

    for index, position in enumerate(
        WHEEL_ORDER
    ):
        radius_m = (
            static.tyre_radius_m[index]
        )

        wheel_speed_kmh = (
            physics.wheel_angular_speed_rad_s[
                index
            ]
            * radius_m
            * 3.6
        )

        wheels[position] = (
            WheelTelemetry(
                pressure_psi=(
                    physics.wheel_pressure_psi[
                        index
                    ]
                ),
                tyre_temp_inner_c=(
                    physics.tyre_temp_inner_c[
                        index
                    ]
                ),
                tyre_temp_middle_c=(
                    physics.tyre_temp_middle_c[
                        index
                    ]
                ),
                tyre_temp_outer_c=(
                    physics.tyre_temp_outer_c[
                        index
                    ]
                ),
                tyre_temp_core_c=(
                    physics.tyre_core_temp_c[
                        index
                    ]
                ),
                brake_temp_c=(
                    physics.brake_temp_c[index]
                ),
                wheel_speed_kmh=(
                    wheel_speed_kmh
                ),
                load_n=(
                    physics.wheel_load_n[index]
                ),
                slip_ratio=(
                    physics.wheel_slip[index]
                ),

                # We leave slip angle at zero until
                # the real AC memory layout is
                # verified on the PC with the game.
                slip_angle_deg=0.0,

                suspension_travel_mm=(
                    physics.suspension_travel_m[
                        index
                    ]
                    * 1000.0
                ),
            )
        )

    vehicle = VehicleTelemetry(
        speed_kmh=physics.speed_kmh,
        rpm=physics.rpm,
        gear=normalize_gear(
            physics.gear_raw
        ),
        throttle=clamp(
            physics.gas,
            0.0,
            1.0,
        ),
        brake=clamp(
            physics.brake,
            0.0,
            1.0,
        ),
        clutch=clamp(
            physics.clutch,
            0.0,
            1.0,
        ),
        steering_angle_deg=degrees(
            physics.steer_angle_rad
        ),
        lateral_g=(
            physics.lateral_g
        ),
        longitudinal_g=(
            physics.longitudinal_g
        ),
        fuel_l=max(
            0.0,
            physics.fuel_l,
        ),
        brake_bias=clamp(
            physics.brake_bias,
            0.0,
            1.0,
        ),
        pitch_deg=degrees(
            physics.pitch_rad
        ),
        roll_deg=degrees(
            physics.roll_rad
        ),
        ride_height_front_mm=(
            physics.ride_height_m[0]
            * 1000.0
        ),
        ride_height_rear_mm=(
            physics.ride_height_m[1]
            * 1000.0
        ),
    )

    environment = (
        EnvironmentTelemetry(
            air_temperature_c=(
                physics.air_temp_c
            ),
            track_temperature_c=(
                physics.road_temp_c
            ),
            grip_level=clamp(
                graphics.surface_grip,
                0.0,
                1.0,
            ),
        )
    )

    return TelemetryFrame(
        timestamp=timestamp,
        session_id=session_id,
        sample_index=sample_index,
        elapsed_seconds=(
            elapsed_seconds
        ),
        car_id=static.car_model,
        track_id=static.track,
        vehicle=vehicle,
        environment=environment,
        wheels=wheels,
    )