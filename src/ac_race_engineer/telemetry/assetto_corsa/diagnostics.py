from dataclasses import dataclass

from ac_race_engineer.telemetry.assetto_corsa.comparison import (
    LapComparison,
    SectorDelta,
)


@dataclass(frozen=True)
class SectorImpact:
    sector_number: int
    delta_ms: int


@dataclass(frozen=True)
class LapComparisonDiagnosis:
    session_id: str

    reference_lap_number: int
    target_lap_number: int

    total_delta_ms: int

    target_is_faster: bool
    target_is_slower: bool
    target_is_equal: bool

    time_gained_ms: int
    time_lost_ms: int

    primary_loss_sector: int | None
    primary_loss_ms: int
    primary_loss_share: float | None

    primary_gain_sector: int | None
    primary_gain_ms: int

    lost_sectors: tuple[
        SectorImpact,
        ...,
    ]

    gained_sectors: tuple[
        SectorImpact,
        ...,
    ]

    neutral_sectors: tuple[int, ...]

    complete_sector_data: bool

    sector_delta_matches_lap_delta: bool

    unexplained_delta_ms: int

    has_actionable_sector_data: bool


class AssettoCorsaDiagnosticService:
    """
    Build deterministic diagnostics from a lap comparison.

    The service does not guess driving causes.

    It only describes what the timing data supports:
    - where time was gained,
    - where time was lost,
    - the biggest loss,
    - the biggest gain,
    - whether sector data is complete,
    - whether sector deltas explain the full lap delta.
    """

    @staticmethod
    def _lost_sectors(
        sectors: tuple[
            SectorDelta,
            ...,
        ],
    ) -> tuple[
        SectorImpact,
        ...,
    ]:
        values = [
            SectorImpact(
                sector_number=(
                    sector.sector_number
                ),
                delta_ms=sector.delta_ms,
            )
            for sector in sectors
            if sector.delta_ms > 0
        ]

        values.sort(
            key=lambda sector: (
                sector.delta_ms
            ),
            reverse=True,
        )

        return tuple(
            values
        )

    @staticmethod
    def _gained_sectors(
        sectors: tuple[
            SectorDelta,
            ...,
        ],
    ) -> tuple[
        SectorImpact,
        ...,
    ]:
        values = [
            SectorImpact(
                sector_number=(
                    sector.sector_number
                ),
                delta_ms=sector.delta_ms,
            )
            for sector in sectors
            if sector.delta_ms < 0
        ]

        values.sort(
            key=lambda sector: (
                sector.delta_ms
            )
        )

        return tuple(
            values
        )

    @staticmethod
    def _neutral_sectors(
        sectors: tuple[
            SectorDelta,
            ...,
        ],
    ) -> tuple[int, ...]:
        return tuple(
            sector.sector_number
            for sector in sectors
            if sector.delta_ms == 0
        )

    def diagnose(
        self,
        comparison: LapComparison,
    ) -> LapComparisonDiagnosis:
        lost_sectors = (
            self._lost_sectors(
                comparison.sectors
            )
        )

        gained_sectors = (
            self._gained_sectors(
                comparison.sectors
            )
        )

        neutral_sectors = (
            self._neutral_sectors(
                comparison.sectors
            )
        )

        primary_loss_sector = None
        primary_loss_ms = 0
        primary_loss_share = None

        if lost_sectors:
            primary_loss = (
                lost_sectors[0]
            )

            primary_loss_sector = (
                primary_loss.sector_number
            )

            primary_loss_ms = (
                primary_loss.delta_ms
            )

            if (
                comparison.time_lost_ms
                > 0
            ):
                primary_loss_share = (
                    primary_loss_ms
                    / comparison.time_lost_ms
                )

        primary_gain_sector = None
        primary_gain_ms = 0

        if gained_sectors:
            primary_gain = (
                gained_sectors[0]
            )

            primary_gain_sector = (
                primary_gain.sector_number
            )

            primary_gain_ms = abs(
                primary_gain.delta_ms
            )

        unexplained_delta_ms = (
            comparison.total_delta_ms
            - comparison.sector_delta_total_ms
        )

        sector_delta_matches_lap_delta = (
            unexplained_delta_ms == 0
        )

        has_actionable_sector_data = (
            bool(
                comparison.sectors
            )
            and (
                bool(lost_sectors)
                or bool(gained_sectors)
            )
        )

        return LapComparisonDiagnosis(
            session_id=(
                comparison.session_id
            ),
            reference_lap_number=(
                comparison.reference_lap_number
            ),
            target_lap_number=(
                comparison.target_lap_number
            ),
            total_delta_ms=(
                comparison.total_delta_ms
            ),
            target_is_faster=(
                comparison.total_delta_ms
                < 0
            ),
            target_is_slower=(
                comparison.total_delta_ms
                > 0
            ),
            target_is_equal=(
                comparison.total_delta_ms
                == 0
            ),
            time_gained_ms=(
                comparison.time_gained_ms
            ),
            time_lost_ms=(
                comparison.time_lost_ms
            ),
            primary_loss_sector=(
                primary_loss_sector
            ),
            primary_loss_ms=(
                primary_loss_ms
            ),
            primary_loss_share=(
                primary_loss_share
            ),
            primary_gain_sector=(
                primary_gain_sector
            ),
            primary_gain_ms=(
                primary_gain_ms
            ),
            lost_sectors=(
                lost_sectors
            ),
            gained_sectors=(
                gained_sectors
            ),
            neutral_sectors=(
                neutral_sectors
            ),
            complete_sector_data=(
                comparison.complete_sector_comparison
            ),
            sector_delta_matches_lap_delta=(
                sector_delta_matches_lap_delta
            ),
            unexplained_delta_ms=(
                unexplained_delta_ms
            ),
            has_actionable_sector_data=(
                has_actionable_sector_data
            ),
        )