from datetime import UTC, datetime

from ac_race_engineer.telemetry.models import (
    EnvironmentTelemetry,
    TelemetryFrame,
    VehicleTelemetry,
    WheelTelemetry,
)


def test_create_telemetry_frame():

    wheel = WheelTelemetry(
        pressure_psi=26.5,
        tyre_temp_inner_c=82.0,
        tyre_temp_middle_c=80.0,
        tyre_temp_outer_c=78.0,
        tyre_temp_core_c=80.0,
        brake_temp_c=350.0,
        wheel_speed_kmh=120.0,
        load_n=3200.0,
        slip_ratio=0.03,
        slip_angle_deg=3.2,
        suspension_travel_mm=55.0,
    )

    vehicle = VehicleTelemetry(
        speed_kmh=120.0,
        rpm=5500,
        gear=4,
        throttle=0.75,
        brake=0.0,
        clutch=0.0,
        steering_angle_deg=8.0,
        lateral_g=0.8,
        longitudinal_g=0.2,
        fuel_l=25.0,
        brake_bias=0.64,
        pitch_deg=0.2,
        roll_deg=1.1,
        ride_height_front_mm=70.0,
        ride_height_rear_mm=75.0,
    )

    environment = EnvironmentTelemetry(
        air_temperature_c=23.0,
        track_temperature_c=31.0,
        grip_level=0.97,
    )

    frame = TelemetryFrame(
        timestamp=datetime.now(UTC),
        session_id="test-session",
        sample_index=1,
        elapsed_seconds=0.05,
        car_id="mazda_mx5",
        track_id="test_track",
        vehicle=vehicle,
        environment=environment,
        wheels={
            "FL": wheel,
            "FR": wheel,
            "RL": wheel,
            "RR": wheel,
        },
    )

    assert frame.vehicle.speed_kmh == 120.0
    assert frame.vehicle.gear == 4
    assert len(frame.wheels) == 4
    assert frame.wheels["FL"].pressure_psi == 26.5