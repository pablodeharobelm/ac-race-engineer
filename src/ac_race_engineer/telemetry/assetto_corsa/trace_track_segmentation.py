from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.trace_braking import (
    BrakingZone,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_entry import (
    CornerEntry,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_corner_exit import (
    CornerExit,
)


@dataclass(frozen=True)
class TrackCornerSegment:
    corner_number: int

    braking_zone: BrakingZone
    entry: CornerEntry
    corner_exit: CornerExit

    @property
    def braking_zone_number(
        self,
    ) -> int:
        return self.braking_zone.zone_number

    @property
    def entry_number(
        self,
    ) -> int:
        return self.entry.entry_number

    @property
    def exit_number(
        self,
    ) -> int:
        return self.corner_exit.exit_number

    @property
    def start_progress(
        self,
    ) -> float:
        return self.braking_zone.start_progress

    @property
    def braking_release_progress(
        self,
    ) -> float:
        return self.braking_zone.end_progress

    @property
    def turn_in_progress(
        self,
    ) -> float:
        return self.entry.turn_in_progress

    @property
    def apex_progress(
        self,
    ) -> float:
        return self.entry.apex_progress

    @property
    def throttle_application_progress(
        self,
    ) -> float:
        return (
            self.corner_exit
            .throttle_application_progress
        )

    @property
    def exit_progress(
        self,
    ) -> float:
        return self.corner_exit.exit_progress

    @property
    def end_progress(
        self,
    ) -> float:
        return self.corner_exit.exit_progress

    @property
    def minimum_speed_kmh(
        self,
    ) -> float:
        return (
            self.braking_zone
            .minimum_speed_kmh
        )

    @property
    def apex_speed_kmh(
        self,
    ) -> float:
        return self.entry.apex_speed_kmh

    @property
    def exit_speed_kmh(
        self,
    ) -> float:
        return (
            self.corner_exit
            .exit_speed_kmh
        )

    @property
    def total_duration_seconds(
        self,
    ) -> float:
        return max(
            0.0,
            (
                self.corner_exit
                .exit_elapsed_seconds
                - self.braking_zone
                .start_elapsed_seconds
            ),
        )

    @property
    def progress_span(
        self,
    ) -> float:
        return max(
            0.0,
            (
                self.end_progress
                - self.start_progress
            ),
        )


@dataclass(frozen=True)
class TrackSegmentationResult:
    corners: tuple[
        TrackCornerSegment,
        ...,
    ]

    unmatched_braking_zone_numbers: tuple[
        int,
        ...,
    ]

    unmatched_entry_numbers: tuple[
        int,
        ...,
    ]

    unmatched_exit_numbers: tuple[
        int,
        ...,
    ]

    @property
    def corner_count(
        self,
    ) -> int:
        return len(
            self.corners
        )

    @property
    def is_complete(
        self,
    ) -> bool:
        return not (
            self.unmatched_braking_zone_numbers
            or self.unmatched_entry_numbers
            or self.unmatched_exit_numbers
        )


class AssettoCorsaTrackSegmentationService:
    """
    Build logical track corners from braking, entry and
    exit telemetry phases.

    Relationships:

        CornerEntry.source_braking_zone_number
            -> BrakingZone.zone_number

        CornerExit.source_entry_number
            -> CornerEntry.entry_number

    Only complete chains become TrackCornerSegment objects.

    Corner numbers are generated from physical track order
    using apex position, not source object numbering.
    """

    def __init__(
        self,
        *,
        apex_link_tolerance: float = 0.02,
    ) -> None:
        if not (
            0.0
            <= apex_link_tolerance
            <= 1.0
        ):
            raise ValueError(
                "apex_link_tolerance must "
                "be between 0 and 1"
            )

        self.apex_link_tolerance = (
            apex_link_tolerance
        )

    @staticmethod
    def _index_braking_zones(
        braking_zones: tuple[
            BrakingZone,
            ...,
        ],
    ) -> dict[
        int,
        BrakingZone,
    ]:
        result: dict[
            int,
            BrakingZone,
        ] = {}

        for zone in braking_zones:
            if zone.zone_number in result:
                raise ValueError(
                    "Duplicate braking zone number: "
                    f"{zone.zone_number}"
                )

            result[
                zone.zone_number
            ] = zone

        return result

    @staticmethod
    def _index_entries(
        entries: tuple[
            CornerEntry,
            ...,
        ],
    ) -> dict[
        int,
        CornerEntry,
    ]:
        result: dict[
            int,
            CornerEntry,
        ] = {}

        linked_braking_zones: set[
            int
        ] = set()

        for entry in entries:
            if entry.entry_number in result:
                raise ValueError(
                    "Duplicate corner entry number: "
                    f"{entry.entry_number}"
                )

            if (
                entry.source_braking_zone_number
                in linked_braking_zones
            ):
                raise ValueError(
                    "Multiple corner entries reference "
                    "the same braking zone: "
                    f"{entry.source_braking_zone_number}"
                )

            result[
                entry.entry_number
            ] = entry

            linked_braking_zones.add(
                entry.source_braking_zone_number
            )

        return result

    @staticmethod
    def _index_exits_by_entry(
        exits: tuple[
            CornerExit,
            ...,
        ],
    ) -> dict[
        int,
        CornerExit,
    ]:
        exit_numbers: set[
            int
        ] = set()

        result: dict[
            int,
            CornerExit,
        ] = {}

        for corner_exit in exits:
            if (
                corner_exit.exit_number
                in exit_numbers
            ):
                raise ValueError(
                    "Duplicate corner exit number: "
                    f"{corner_exit.exit_number}"
                )

            if (
                corner_exit.source_entry_number
                in result
            ):
                raise ValueError(
                    "Multiple corner exits reference "
                    "the same corner entry: "
                    f"{corner_exit.source_entry_number}"
                )

            exit_numbers.add(
                corner_exit.exit_number
            )

            result[
                corner_exit.source_entry_number
            ] = corner_exit

        return result

    def _validate_chain(
        self,
        *,
        zone: BrakingZone,
        entry: CornerEntry,
        corner_exit: CornerExit,
    ) -> None:
        apex_difference = abs(
            corner_exit.apex_progress
            - entry.apex_progress
        )

        if (
            apex_difference
            > self.apex_link_tolerance
        ):
            raise ValueError(
                "Corner entry and exit apex "
                "positions do not match"
            )

        if (
            entry.turn_in_progress
            < zone.start_progress
        ):
            raise ValueError(
                "Turn-in cannot occur before "
                "the braking zone starts"
            )

        if (
            entry.apex_progress
            < entry.turn_in_progress
        ):
            raise ValueError(
                "Apex cannot occur before turn-in"
            )

        if (
            corner_exit.exit_progress
            < entry.apex_progress
        ):
            raise ValueError(
                "Corner exit cannot occur "
                "before the apex"
            )

    def segment(
        self,
        *,
        braking_zones: tuple[
            BrakingZone,
            ...,
        ],
        entries: tuple[
            CornerEntry,
            ...,
        ],
        exits: tuple[
            CornerExit,
            ...,
        ],
    ) -> TrackSegmentationResult:
        zones_by_number = (
            self._index_braking_zones(
                braking_zones
            )
        )

        self._index_entries(
            entries
        )

        exits_by_entry = (
            self._index_exits_by_entry(
                exits
            )
        )

        complete_chains: list[
            tuple[
                BrakingZone,
                CornerEntry,
                CornerExit,
            ]
        ] = []

        used_zones: set[
            int
        ] = set()

        used_entries: set[
            int
        ] = set()

        used_exits: set[
            int
        ] = set()

        for entry in entries:
            zone = zones_by_number.get(
                entry.source_braking_zone_number
            )

            corner_exit = (
                exits_by_entry.get(
                    entry.entry_number
                )
            )

            if (
                zone is None
                or corner_exit is None
            ):
                continue

            self._validate_chain(
                zone=zone,
                entry=entry,
                corner_exit=corner_exit,
            )

            complete_chains.append(
                (
                    zone,
                    entry,
                    corner_exit,
                )
            )

        complete_chains.sort(
            key=lambda chain: (
                chain[1].apex_progress
            )
        )

        corners: list[
            TrackCornerSegment
        ] = []

        for (
            index,
            chain,
        ) in enumerate(
            complete_chains,
            start=1,
        ):
            (
                zone,
                entry,
                corner_exit,
            ) = chain

            corners.append(
                TrackCornerSegment(
                    corner_number=index,
                    braking_zone=zone,
                    entry=entry,
                    corner_exit=(
                        corner_exit
                    ),
                )
            )

            used_zones.add(
                zone.zone_number
            )

            used_entries.add(
                entry.entry_number
            )

            used_exits.add(
                corner_exit.exit_number
            )

        unmatched_zones = tuple(
            zone.zone_number
            for zone in braking_zones
            if (
                zone.zone_number
                not in used_zones
            )
        )

        unmatched_entries = tuple(
            entry.entry_number
            for entry in entries
            if (
                entry.entry_number
                not in used_entries
            )
        )

        unmatched_exits = tuple(
            corner_exit.exit_number
            for corner_exit in exits
            if (
                corner_exit.exit_number
                not in used_exits
            )
        )

        return TrackSegmentationResult(
            corners=tuple(
                corners
            ),
            unmatched_braking_zone_numbers=(
                unmatched_zones
            ),
            unmatched_entry_numbers=(
                unmatched_entries
            ),
            unmatched_exit_numbers=(
                unmatched_exits
            ),
        )