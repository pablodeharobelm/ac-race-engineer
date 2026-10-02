from fastapi import (
    FastAPI,
    HTTPException,
    Query,
)

from ac_race_engineer.api.schemas import (
    HealthResponse,
    RaceEngineerAnalysisRequest,
    RaceEngineerAnalysisResponse,
    StoredRaceEngineerAnalysisResponse,
)
from ac_race_engineer.telemetry.assetto_corsa.race_engineer_llm_factory import (
    create_race_engineer_explanation_service,
)
from ac_race_engineer.telemetry.assetto_corsa.race_engineer_persistence import (
    AssettoCorsaRaceEngineerPersistenceManager,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_pipeline import (
    AssettoCorsaRaceEngineerPipeline,
)


def create_app(
    *,
    pipeline: (
        AssettoCorsaRaceEngineerPipeline
        | None
    ) = None,
    persistence_manager: (
        AssettoCorsaRaceEngineerPersistenceManager
        | None
    ) = None,
) -> FastAPI:
    if pipeline is None:
        explanation_service = (
            create_race_engineer_explanation_service()
        )

        race_engineer_pipeline = (
            AssettoCorsaRaceEngineerPipeline(
                explanation_service=(
                    explanation_service
                )
            )
        )

    else:
        race_engineer_pipeline = (
            pipeline
        )

    app = FastAPI(
        title="AC Race Engineer API",
        description=(
            "Telemetry analysis and deterministic "
            "race-engineering API for Assetto Corsa."
        ),
        version="0.1.0",
    )

    def require_persistence(
    ) -> AssettoCorsaRaceEngineerPersistenceManager:
        if persistence_manager is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Race Engineer persistence "
                    "is not configured"
                ),
            )

        return persistence_manager

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
    )
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="ac-race-engineer",
            version="0.1.0",
        )

    @app.post(
        "/v1/race-engineer/analyze",
        response_model=(
            RaceEngineerAnalysisResponse
        ),
        tags=["race-engineer"],
    )
    def analyze(
        request: RaceEngineerAnalysisRequest,
    ) -> RaceEngineerAnalysisResponse:
        if (
            request.reference_lap_number
            == request.target_lap_number
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Reference and target laps "
                    "must be different"
                ),
            )

        reference_trace = tuple(
            sample.to_domain()
            for sample
            in request.reference_trace
        )

        target_trace = tuple(
            sample.to_domain()
            for sample
            in request.target_trace
        )

        try:
            result = (
                race_engineer_pipeline.run(
                    reference_lap_number=(
                        request
                        .reference_lap_number
                    ),
                    target_lap_number=(
                        request
                        .target_lap_number
                    ),
                    reference_trace=(
                        reference_trace
                    ),
                    target_trace=(
                        target_trace
                    ),
                    grid_points=(
                        request.grid_points
                    ),
                    explain=request.explain,
                    language=(
                        request.language
                    ),
                )
            )

        except ValueError as exc:
            message = str(
                exc
            )

            if (
                request.explain
                and "explanation_service"
                in message
            ):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "LLM explanation service "
                        "is not configured"
                    ),
                ) from exc

            raise HTTPException(
                status_code=400,
                detail=message,
            ) from exc

        except RuntimeError as exc:
            if request.explain:
                raise HTTPException(
                    status_code=502,
                    detail=str(
                        exc
                    ),
                ) from exc

            raise

        analysis_id = None

        if request.persist:
            manager = require_persistence()

            try:
                stored = manager.save(
                    result,
                    session_id=(
                        request.session_id
                    ),
                )

            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=str(
                        exc
                    ),
                ) from exc

            analysis_id = stored.id

        return (
            RaceEngineerAnalysisResponse
            .from_pipeline_result(
                result,
                analysis_id=analysis_id,
            )
        )

    @app.get(
        "/v1/race-engineer/analyses/recent",
        response_model=list[
            StoredRaceEngineerAnalysisResponse
        ],
        tags=["race-engineer"],
    )
    def recent_analyses(
        limit: int = Query(
            default=20,
            ge=1,
            le=100,
        ),
    ) -> list[
        StoredRaceEngineerAnalysisResponse
    ]:
        manager = require_persistence()

        records = manager.list_recent(
            limit=limit
        )

        return [
            StoredRaceEngineerAnalysisResponse
            .from_record(
                record
            )
            for record in records
        ]

    @app.get(
        (
            "/v1/race-engineer/"
            "analyses/session/{session_id}"
        ),
        response_model=list[
            StoredRaceEngineerAnalysisResponse
        ],
        tags=["race-engineer"],
    )
    def session_analyses(
        session_id: str,
    ) -> list[
        StoredRaceEngineerAnalysisResponse
    ]:
        manager = require_persistence()

        try:
            records = (
                manager.list_for_session(
                    session_id
                )
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(
                    exc
                ),
            ) from exc

        return [
            StoredRaceEngineerAnalysisResponse
            .from_record(
                record
            )
            for record in records
        ]

    @app.get(
        (
            "/v1/race-engineer/"
            "analyses/{analysis_id}"
        ),
        response_model=(
            StoredRaceEngineerAnalysisResponse
        ),
        tags=["race-engineer"],
    )
    def get_analysis(
        analysis_id: str,
    ) -> StoredRaceEngineerAnalysisResponse:
        manager = require_persistence()

        record = manager.get_by_id(
            analysis_id
        )

        if record is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Race Engineer analysis "
                    "not found"
                ),
            )

        return (
            StoredRaceEngineerAnalysisResponse
            .from_record(
                record
            )
        )

    return app


app = create_app()