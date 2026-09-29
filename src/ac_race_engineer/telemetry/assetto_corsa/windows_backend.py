import ctypes
import mmap
import sys
from collections.abc import Callable
from ctypes import sizeof, wintypes
from typing import Protocol, TypeVar

from typing_extensions import Self

from ac_race_engineer.telemetry.assetto_corsa.backend import (
    AssettoCorsaBackend,
)
from ac_race_engineer.telemetry.assetto_corsa.exceptions import (
    AssettoCorsaReadError,
    AssettoCorsaUnavailableError,
)
from ac_race_engineer.telemetry.assetto_corsa.snapshots import (
    ACGraphicsSnapshot,
    ACPhysicsSnapshot,
    ACStaticSnapshot,
)
from ac_race_engineer.telemetry.assetto_corsa.structs import (
    ACGraphicsPage,
    ACPhysicsPage,
    ACStaticPage,
    decode_utf16,
)

PHYSICS_MAPPING = r"Local\acpmf_physics"
GRAPHICS_MAPPING = r"Local\acpmf_graphics"
STATIC_MAPPING = r"Local\acpmf_static"

FILE_MAP_READ = 0x0004


class ReadableMapping(Protocol):
    def seek(
        self,
        offset: int,
    ) -> int:
        ...

    def read(
        self,
        size: int,
    ) -> bytes:
        ...

    def close(
        self,
    ) -> None:
        ...


MappingFactory = Callable[
    [int, str],
    ReadableMapping,
]


StructureType = TypeVar(
    "StructureType",
    bound=ctypes.Structure,
)


def _mapping_exists(
    name: str,
) -> bool:
    if sys.platform != "win32":
        return False

    kernel32 = ctypes.WinDLL(
        "kernel32",
        use_last_error=True,
    )

    open_file_mapping = (
        kernel32.OpenFileMappingW
    )

    open_file_mapping.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]

    open_file_mapping.restype = (
        wintypes.HANDLE
    )

    close_handle = (
        kernel32.CloseHandle
    )

    close_handle.argtypes = [
        wintypes.HANDLE,
    ]

    close_handle.restype = (
        wintypes.BOOL
    )

    handle = open_file_mapping(
        FILE_MAP_READ,
        False,
        name,
    )

    if not handle:
        return False

    close_handle(handle)

    return True


def _windows_mapping_factory(
    size: int,
    name: str,
) -> ReadableMapping:
    if sys.platform != "win32":
        raise AssettoCorsaUnavailableError(
            "Assetto Corsa shared memory "
            "is only available on Windows"
        )

    if not _mapping_exists(name):
        raise AssettoCorsaUnavailableError(
            "Assetto Corsa shared memory "
            f"is not available: {name}"
        )

    try:
        return mmap.mmap(
            -1,
            size,
            tagname=name,
            access=mmap.ACCESS_READ,
        )

    except OSError as exc:
        raise AssettoCorsaUnavailableError(
            "Unable to open Assetto Corsa "
            f"shared memory: {name}"
        ) from exc


def _tuple4(
    value: object,
) -> tuple[
    float,
    float,
    float,
    float,
]:
    return (
        float(value[0]),
        float(value[1]),
        float(value[2]),
        float(value[3]),
    )


class WindowsSharedMemoryBackend(
    AssettoCorsaBackend
):
    """
    Read Assetto Corsa telemetry from Windows
    shared memory.

    A custom mapping factory can be injected for
    unit tests, allowing the backend to work
    without Assetto Corsa running.
    """

    def __init__(
        self,
        mapping_factory: MappingFactory | None = None,
    ) -> None:
        self._mapping_factory = (
            mapping_factory
            or _windows_mapping_factory
        )

        self._physics_mapping: (
            ReadableMapping | None
        ) = None

        self._graphics_mapping: (
            ReadableMapping | None
        ) = None

        self._static_mapping: (
            ReadableMapping | None
        ) = None

        try:
            self._physics_mapping = (
                self._mapping_factory(
                    sizeof(
                        ACPhysicsPage
                    ),
                    PHYSICS_MAPPING,
                )
            )

            self._graphics_mapping = (
                self._mapping_factory(
                    sizeof(
                        ACGraphicsPage
                    ),
                    GRAPHICS_MAPPING,
                )
            )

            self._static_mapping = (
                self._mapping_factory(
                    sizeof(
                        ACStaticPage
                    ),
                    STATIC_MAPPING,
                )
            )

        except Exception:
            self.close()
            raise

    @staticmethod
    def _read_struct(
        mapping: ReadableMapping | None,
        structure_type: type[StructureType],
        mapping_name: str,
    ) -> StructureType:
        if mapping is None:
            raise AssettoCorsaReadError(
                "Shared memory mapping "
                f"is closed: {mapping_name}"
            )

        expected_size = sizeof(
            structure_type
        )

        try:
            mapping.seek(0)

            payload = mapping.read(
                expected_size
            )

        except (
            OSError,
            ValueError,
        ) as exc:
            raise AssettoCorsaReadError(
                "Unable to read shared memory "
                f"mapping: {mapping_name}"
            ) from exc

        if len(payload) != expected_size:
            raise AssettoCorsaReadError(
                "Unexpected shared-memory "
                f"size for {mapping_name}: "
                f"expected {expected_size}, "
                f"got {len(payload)}"
            )

        return (
            structure_type.from_buffer_copy(
                payload
            )
        )

    def read_physics(
        self,
    ) -> ACPhysicsSnapshot:
        raw = self._read_struct(
            self._physics_mapping,
            ACPhysicsPage,
            PHYSICS_MAPPING,
        )

        return ACPhysicsSnapshot(
            packet_id=int(
                raw.packetId
            ),
            gas=float(
                raw.gas
            ),
            brake=float(
                raw.brake
            ),
            clutch=float(
                raw.clutch
            ),
            fuel_l=float(
                raw.fuel
            ),
            gear_raw=int(
                raw.gear
            ),
            rpm=int(
                raw.rpms
            ),
            steer_angle_rad=float(
                raw.steerAngle
            ),
            speed_kmh=float(
                raw.speedKmh
            ),
            lateral_g=float(
                raw.accG[0]
            ),
            longitudinal_g=float(
                raw.accG[2]
            ),
            wheel_slip=_tuple4(
                raw.wheelSlip
            ),
            wheel_load_n=_tuple4(
                raw.wheelLoad
            ),
            wheel_pressure_psi=_tuple4(
                raw.wheelsPressure
            ),
            wheel_angular_speed_rad_s=_tuple4(
                raw.wheelAngularSpeed
            ),
            tyre_core_temp_c=_tuple4(
                raw.tyreCoreTemperature
            ),
            tyre_temp_inner_c=_tuple4(
                raw.tyreTempI
            ),
            tyre_temp_middle_c=_tuple4(
                raw.tyreTempM
            ),
            tyre_temp_outer_c=_tuple4(
                raw.tyreTempO
            ),
            brake_temp_c=_tuple4(
                raw.brakeTemp
            ),
            suspension_travel_m=_tuple4(
                raw.suspensionTravel
            ),
            brake_bias=float(
                raw.brakeBias
            ),
            pitch_rad=float(
                raw.pitch
            ),
            roll_rad=float(
                raw.roll
            ),
            ride_height_m=(
                float(
                    raw.rideHeight[0]
                ),
                float(
                    raw.rideHeight[1]
                ),
            ),
            air_temp_c=float(
                raw.airTemp
            ),
            road_temp_c=float(
                raw.roadTemp
            ),
        )

    def read_graphics(
        self,
    ) -> ACGraphicsSnapshot:
        raw = self._read_struct(
            self._graphics_mapping,
            ACGraphicsPage,
            GRAPHICS_MAPPING,
        )

        return ACGraphicsSnapshot(
            packet_id=int(
                raw.packetId
            ),
            status=int(
                raw.status
            ),
            session_type=int(
                raw.session
            ),
            completed_laps=int(
                raw.completedLaps
            ),
            position=int(
                raw.position
            ),
            current_time_ms=int(
                raw.iCurrentTime
            ),
            last_time_ms=int(
                raw.iLastTime
            ),
            best_time_ms=int(
                raw.iBestTime
            ),
            session_time_left=float(
                raw.sessionTimeLeft
            ),
            distance_traveled_m=float(
                raw.distanceTraveled
            ),
            is_in_pit=bool(
                raw.isInPit
            ),
            is_in_pit_lane=bool(
                raw.isInPitLane
            ),
            current_sector_index=int(
                raw.currentSectorIndex
            ),
            last_sector_time_ms=int(
                raw.lastSectorTime
            ),
            number_of_laps=int(
                raw.numberOfLaps
            ),
            surface_grip=float(
                raw.surfaceGrip
            ),
        )

    def read_static(
        self,
    ) -> ACStaticSnapshot:
        raw = self._read_struct(
            self._static_mapping,
            ACStaticPage,
            STATIC_MAPPING,
        )

        return ACStaticSnapshot(
            car_model=decode_utf16(
                raw.carModel
            ),
            track=decode_utf16(
                raw.track
            ),
            max_rpm=int(
                raw.maxRpm
            ),
            max_fuel_l=float(
                raw.maxFuel
            ),
            tyre_radius_m=_tuple4(
                raw.tyreRadius
            ),
        )

    def close(
        self,
    ) -> None:
        for attribute in (
            "_physics_mapping",
            "_graphics_mapping",
            "_static_mapping",
        ):
            mapping = getattr(
                self,
                attribute,
                None,
            )

            if mapping is None:
                continue

            try:
                mapping.close()

            finally:
                setattr(
                    self,
                    attribute,
                    None,
                )

    def __enter__(
        self,
    ) -> Self:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

