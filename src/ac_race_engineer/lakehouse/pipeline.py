from pathlib import Path

from ac_race_engineer.domain.lakehouse import (
    LakehousePipelineResult,
)
from ac_race_engineer.lakehouse.bronze import (
    BronzeTelemetryIngestor,
)
from ac_race_engineer.lakehouse.gold import (
    GoldSessionAggregator,
)
from ac_race_engineer.lakehouse.silver import (
    SilverTelemetryProcessor,
)


class LakehousePipeline:

    def __init__(
        self,
        bronze_directory: str | Path = (
            "data/bronze/telemetry"
        ),
        silver_directory: str | Path = (
            "data/silver"
        ),
        gold_directory: str | Path = (
            "data/gold/session_summary"
        ),
    ):
        self.bronze = (
            BronzeTelemetryIngestor(
                output_directory=(
                    bronze_directory
                )
            )
        )

        self.silver = (
            SilverTelemetryProcessor(
                output_directory=(
                    silver_directory
                )
            )
        )

        self.gold = (
            GoldSessionAggregator(
                output_directory=(
                    gold_directory
                )
            )
        )

    def run(
        self,
        raw_file: str | Path,
    ) -> LakehousePipelineResult:

        raw_file = Path(
            raw_file
        )

        bronze_result = (
            self.bronze.ingest(
                raw_file
            )
        )

        silver_result = (
            self.silver.process(
                bronze_result.output_file
            )
        )

        gold_result = (
            self.gold.aggregate(
                silver_result.output_file
            )
        )

        session_ids = {
            bronze_result.session_id,
            silver_result.session_id,
            gold_result.session_id,
        }

        if len(session_ids) != 1:
            raise ValueError(
                "Lakehouse stages produced "
                "different session IDs"
            )

        return LakehousePipelineResult(
            session_id=(
                bronze_result.session_id
            ),
            bronze=bronze_result,
            silver=silver_result,
            gold=gold_result,
            status="completed",
        )