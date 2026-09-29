from ac_race_engineer.telemetry.assetto_corsa.backend import (
    AssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
    ACPhysicsSnapshot,
    ACStaticSnapshot,
)


class FakeAssettoCorsaBackend(
    AssettoCorsaBackend
):
    """
    Fake Assetto Corsa telemetry source.

    Allows AssettoCorsaSource and its mapper to be tested
    without Assetto Corsa running.
    """

    def __init__(
        self,
    ) -> None:
        self.packet_id = 0

    def read_physics(
        self,
    ) -> ACPhysicsSnapshot:
        self.packet_id += 1

        return ACPhysicsSnapshot(
            packet_id=self.packet_id,
            gas=0.82,
            brake=0.0,
            clutch=0.0,
            fuel_l=32.4,
            gear_raw=4,
            rpm=6150,
            steer_angle_rad=0.08,
            speed_kmh=143.2,
            lateral_g=0.72,
            longitudinal_g=0.18,
            wheel_slip=(
                0.03,
                0.03,
                0.04,
                0.04,
            ),
            wheel_load_n=(
                3200.0,
                3300.0,
                2950.0,
                3000.0,
            ),
            wheel_pressure_psi=(
                26.1,
                26.0,
                25.8,
                25.9,
            ),
            wheel_angular_speed_rad_s=(
                112.0,
                113.0,
                114.0,
                113.5,
            ),
            tyre_core_temp_c=(
                82.0,
                83.0,
                79.0,
                80.0,
            ),
            tyre_temp_inner_c=(
                86.0,
                87.0,
                82.0,
                83.0,
            ),
            tyre_temp_middle_c=(
                82.0,
                83.0,
                79.0,
                80.0,
            ),
            tyre_temp_outer_c=(
                78.0,
                79.0,
                76.0,
                77.0,
            ),
            brake_temp_c=(
                410.0,
                415.0,
                350.0,
                355.0,
            ),
            suspension_travel_m=(
                0.052,
                0.053,
                0.047,
                0.048,
            ),
            brake_bias=0.64,
            pitch_rad=-0.01,
            roll_rad=0.02,
            ride_height_m=(
                0.068,
                0.074,
            ),
            air_temp_c=24.0,
            road_temp_c=31.0,
        )

    def read_graphics(
        self,
    ) -> ACGraphicsSnapshot:
        return ACGraphicsSnapshot(
            packet_id=self.packet_id,
            status=2,
            session_type=0,
            completed_laps=2,
            position=1,
            current_time_ms=74231,
            last_time_ms=105412,
            best_time_ms=104850,
            session_time_left=1200.0,
            distance_traveled_m=8400.0,
            is_in_pit=False,
            is_in_pit_lane=False,
            current_sector_index=1,
            last_sector_time_ms=34120,
            number_of_laps=0,
            surface_grip=0.98,
        )

    def read_static(
        self,
    ) -> ACStaticSnapshot:
        return ACStaticSnapshot(
            car_model="ks_mazda_mx5_cup",
            track="magione",
            max_rpm=7500,
            max_fuel_l=45.0,
            tyre_radius_m=(
                0.31,
                0.31,
                0.31,
                0.31,
            ),
        )