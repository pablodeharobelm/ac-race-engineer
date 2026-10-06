from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ac_race_engineer.api.capture_schemas import (
    CapturedLapResponse,
    CapturedSessionResponse,
    CapturedTraceResponse,
    StoredLapAnalysisRequest,
)
from ac_race_engineer.api.schemas import (
    DrivingTraceSampleRequest,
    HealthResponse,
    RaceEngineerAnalysisRequest,
    RaceEngineerAnalysisResponse,
    StoredRaceEngineerAnalysisResponse,
)
from ac_race_engineer.database.session import create_database_engine, create_session_factory
from ac_race_engineer.services.captured_sessions import (
    CapturedSessionService,
    CaptureNotFoundError,
    TraceUnavailableError,
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
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    captured_sessions = CapturedSessionService(session_factory) if session_factory else None
    if persistence_manager is None and session_factory is not None:
        persistence_manager = AssettoCorsaRaceEngineerPersistenceManager(session_factory)
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

    @app.exception_handler(CaptureNotFoundError)
    async def capture_not_found(request: Request, exc: CaptureNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TraceUnavailableError)
    async def trace_unavailable(request: Request, exc: TraceUnavailableError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def database_unavailable(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(status_code=503, content={
            "detail": "The database is unavailable. Check the connection and apply migrations.",
        })

    def require_captured_sessions() -> CapturedSessionService:
        if captured_sessions is None:
            raise HTTPException(status_code=503, detail="Captured session storage is not configured")
        return captured_sessions

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

        if request.persist:
            require_persistence()

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

    @app.get("/v1/sessions", response_model=list[CapturedSessionResponse], tags=["sessions"])
    def captured_session_list(limit: int = Query(default=20, ge=1, le=100)):
        return require_captured_sessions().list_recent(limit=limit)

    @app.get(
        "/v1/sessions/{session_id}/laps",
        response_model=list[CapturedLapResponse], tags=["sessions"],
    )
    def captured_laps(session_id: str):
        return require_captured_sessions().list_laps(session_id)

    @app.get(
        "/v1/sessions/{session_id}/laps/{lap_number}/trace",
        response_model=CapturedTraceResponse, tags=["sessions"],
    )
    def captured_trace(session_id: str, lap_number: int):
        if lap_number <= 0:
            raise HTTPException(status_code=400, detail="lap_number must be greater than 0")
        trace = require_captured_sessions().read_trace(session_id, lap_number)
        return CapturedTraceResponse(
            session_id=trace.session_id, lap_number=trace.lap_number,
            lap_time_ms=trace.lap_time_ms,
            samples=[DrivingTraceSampleRequest(**asdict(sample)) for sample in trace.samples],
        )

    @app.post(
        "/v1/sessions/{session_id}/analyze",
        response_model=RaceEngineerAnalysisResponse, tags=["sessions"],
    )
    def analyze_captured_laps(session_id: str, request: StoredLapAnalysisRequest):
        if request.reference_lap_number == request.target_lap_number:
            raise HTTPException(status_code=400, detail="Reference and target laps must be different")
        if request.persist:
            require_persistence()
        service = require_captured_sessions()
        reference = service.read_trace(session_id, request.reference_lap_number)
        target = service.read_trace(session_id, request.target_lap_number)
        return analyze(RaceEngineerAnalysisRequest(
            **request.model_dump(), session_id=session_id,
            reference_trace=[asdict(sample) for sample in reference.samples],
            target_trace=[asdict(sample) for sample in target.samples],
        ))

    return app


def create_local_app() -> FastAPI:
    """Uvicorn factory for local capture, browsing and persisted analysis."""
    engine = create_database_engine()
    try:
        local_app = create_app(session_factory=create_session_factory(engine))
    except Exception:
        engine.dispose()
        raise

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    local_app.router.lifespan_context = lifespan
    return local_app


app = create_app()
