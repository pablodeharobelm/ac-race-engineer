from dataclasses import dataclass

from sqlalchemy.orm import Session

from ac_race_engineer.telemetry.assetto_corsa.history import (
    AssettoCorsaHistoryService,
    LapHistory,
    SectorHistory,
)


@dataclass(frozen=True)
class SectorDelta:
    sector_number: int

    reference_time_ms: int
    target_time_ms: int

    delta_ms: int


@dataclass(frozen=True)
class LapComparison:
    session_id: str

    reference_lap_number: int
    target_lap_number: int

    reference_lap_time_ms: int
    target_lap_time_ms: int

    total_delta_ms: int

    sectors: tuple[
        SectorDelta,
        ...,
    ]

    sector_delta_total_ms: int

    time_gained_ms: int
    time_lost_ms: int

    biggest_gain_sector: int | None
    biggest_loss_sector: int | None

    complete_sector_comparison: bool


class AssettoCorsaLapComparisonService:
    """
    Compare two persisted laps from the same session.

    Delta convention:

        target - reference

    Therefore:
    - negative delta -> target is faster
    - positive delta -> target is slower
    """

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.history = (
            AssettoCorsaHistoryService(
                session
            )
        )

    @staticmethod
    def _find_lap(
        laps: tuple[LapHistory, ...],
        lap_number: int,
    ) -> LapHistory:
        for lap in laps:
            if (
                lap.lap_number
                == lap_number
            ):
                return lap

        raise ValueError(
            f"Lap not found: {lap_number}"
        )

    @staticmethod
    def _sectors_by_number(
        lap: LapHistory,
    ) -> dict[int, SectorHistory]:
        return {
            sector.sector_number: sector
            for sector in lap.sectors
            if sector.sector_time_ms > 0
        }

    def compare(
        self,
        *,
        session_id: str,
        reference_lap_number: int,
        target_lap_number: int,
    ) -> LapComparison:
        if (
            reference_lap_number
            == target_lap_number
        ):
            raise ValueError(
                "Reference and target laps "
                "must be different"
            )

        summary = (
            self.history.get_summary(
                session_id
            )
        )

        reference = self._find_lap(
            summary.laps,
            reference_lap_number,
        )

        target = self._find_lap(
            summary.laps,
            target_lap_number,
        )

        reference_sectors = (
            self._sectors_by_number(
                reference
            )
        )

        target_sectors = (
            self._sectors_by_number(
                target
            )
        )

        shared_sector_numbers = sorted(
            set(
                reference_sectors
            )
            & set(
                target_sectors
            )
        )

        sector_deltas: list[
            SectorDelta
        ] = []

        for sector_number in (
            shared_sector_numbers
        ):
            reference_sector = (
                reference_sectors[
                    sector_number
                ]
            )

            target_sector = (
                target_sectors[
                    sector_number
                ]
            )

            delta_ms = (
                target_sector.sector_time_ms
                - reference_sector.sector_time_ms
            )

            sector_deltas.append(
                SectorDelta(
                    sector_number=(
                        sector_number
                    ),
                    reference_time_ms=(
                        reference_sector.sector_time_ms
                    ),
                    target_time_ms=(
                        target_sector.sector_time_ms
                    ),
                    delta_ms=delta_ms,
                )
            )

        sector_delta_total_ms = sum(
            sector.delta_ms
            for sector in sector_deltas
        )

        time_gained_ms = sum(
            -sector.delta_ms
            for sector in sector_deltas
            if sector.delta_ms < 0
        )

        time_lost_ms = sum(
            sector.delta_ms
            for sector in sector_deltas
            if sector.delta_ms > 0
        )

        gain_candidates = [
            sector
            for sector in sector_deltas
            if sector.delta_ms < 0
        ]

        loss_candidates = [
            sector
            for sector in sector_deltas
            if sector.delta_ms > 0
        ]

        biggest_gain_sector = None

        if gain_candidates:
            biggest_gain_sector = min(
                gain_candidates,
                key=lambda sector: (
                    sector.delta_ms
                ),
            ).sector_number

        biggest_loss_sector = None

        if loss_candidates:
            biggest_loss_sector = max(
                loss_candidates,
                key=lambda sector: (
                    sector.delta_ms
                ),
            ).sector_number

        complete_sector_comparison = (
            bool(
                reference_sectors
            )
            and (
                set(reference_sectors)
                == set(target_sectors)
            )
        )

        return LapComparison(
            session_id=session_id,
            reference_lap_number=(
                reference_lap_number
            ),
            target_lap_number=(
                target_lap_number
            ),
            reference_lap_time_ms=(
                reference.lap_time_ms
            ),
            target_lap_time_ms=(
                target.lap_time_ms
            ),
            total_delta_ms=(
                target.lap_time_ms
                - reference.lap_time_ms
            ),
            sectors=tuple(
                sector_deltas
            ),
            sector_delta_total_ms=(
                sector_delta_total_ms
            ),
            time_gained_ms=(
                time_gained_ms
            ),
            time_lost_ms=(
                time_lost_ms
            ),
            biggest_gain_sector=(
                biggest_gain_sector
            ),
            biggest_loss_sector=(
                biggest_loss_sector
            ),
            complete_sector_comparison=(
                complete_sector_comparison
            ),
        )

    def compare_to_best(
        self,
        *,
        session_id: str,
        lap_number: int,
    ) -> LapComparison:
        summary = (
            self.history.get_summary(
                session_id
            )
        )

        best_lap_number = (
            summary.best_lap_number
        )

        if best_lap_number is None:
            raise ValueError(
                "Session has no valid laps"
            )

        if (
            lap_number
            == best_lap_number
        ):
            raise ValueError(
                "The selected lap is already "
                "the session best"
            )

        return self.compare(
            session_id=session_id,
            reference_lap_number=(
                best_lap_number
            ),
            target_lap_number=(
                lap_number
            ),
        )