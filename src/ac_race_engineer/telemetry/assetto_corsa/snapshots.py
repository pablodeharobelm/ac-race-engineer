from dataclasses import dataclass


@dataclass(frozen=True)
class ACPhysicsSnapshot:
    packet_id: int

    gas: float
    brake: float
    clutch: float

    fuel_l: float

    gear_raw: int
    rpm: int

    steer_angle_rad: float
    speed_kmh: float

    lateral_g: float
    longitudinal_g: float

    wheel_slip: tuple[
        float,
        float,
        float,
        float,
    ]

    wheel_load_n: tuple[
        float,
        float,
        float,
        float,
    ]

    wheel_pressure_psi: tuple[
        float,
        float,
        float,
        float,
    ]

    wheel_angular_speed_rad_s: tuple[
        float,
        float,
        float,
        float,
    ]

    tyre_core_temp_c: tuple[
        float,
        float,
        float,
        float,
    ]

    tyre_temp_inner_c: tuple[
        float,
        float,
        float,
        float,
    ]

    tyre_temp_middle_c: tuple[
        float,
        float,
        float,
        float,
    ]

    tyre_temp_outer_c: tuple[
        float,
        float,
        float,
        float,
    ]

    brake_temp_c: tuple[
        float,
        float,
        float,
        float,
    ]

    suspension_travel_m: tuple[
        float,
        float,
        float,
        float,
    ]

    brake_bias: float

    pitch_rad: float
    roll_rad: float

    ride_height_m: tuple[
        float,
        float,
    ]

    air_temp_c: float
    road_temp_c: float


@dataclass(frozen=True)
class ACGraphicsSnapshot:
    packet_id: int

    status: int
    session_type: int

    completed_laps: int
    position: int

    current_time_ms: int
    last_time_ms: int
    best_time_ms: int

    session_time_left: float
    distance_traveled_m: float

    is_in_pit: bool
    is_in_pit_lane: bool

    current_sector_index: int
    last_sector_time_ms: int

    number_of_laps: int

    surface_grip: float
    normalized_car_position: float = 0.0


@dataclass(frozen=True)
class ACStaticSnapshot:
    car_model: str
    track: str

    max_rpm: int
    max_fuel_l: float

    tyre_radius_m: tuple[
        float,
        float,
        float,
        float,
    ]