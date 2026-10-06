# AC Race Engineer

Telemetry and race engineering platform for Assetto Corsa, built in Python.
The goal is to collect driving data and turn lap comparisons into actionable
coaching, while demonstrating data engineering and machine learning workflows.

## Current capabilities

- Windows shared-memory telemetry reader and a fake backend for development.
- Session, lap and sector tracking; dense lap traces stored as Parquet.
- Deterministic lap comparison, braking, corner entry/exit and coaching analysis.
- SQLAlchemy repositories and Alembic migrations for relational metadata.
- FastAPI analysis API and a Streamlit dashboard.
- Browse captured sessions and laps, compare saved Parquet traces, and reopen saved analyses.
- Optional Ollama explanations, plus experimental ML, Kafka and Spark pipelines.

This is a development project. These modules have automated tests, but a complete
capture-to-coaching workflow during a real driving session still needs validation.
The dashboard is an analysis interface; automatic live coaching/audio is not
implemented by the capture command.

For a complete capture-to-dashboard walkthrough without the game or Docker, see
the [local two-lap demo](docs/local-demo.md).

## Quick start (Windows / PowerShell)

Run these commands from the repository root with Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
docker compose up -d postgres
python -m alembic upgrade head
python -m ac_race_engineer.assetto_corsa_capture --fake --samples 100 --quiet
```

The default database URL matches the Docker host port **55432**. Override it when
using another database:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://ac_race:ac_race_dev@localhost:55432/ac_race_engineer"
```

Environment variables must be set in each terminal that needs them. The project
does not automatically load `.env` files. The Compose credentials are for local
development.

## Capture from Assetto Corsa

Start the game and enter an on-track session, then run:

```powershell
python -m ac_race_engineer.assetto_corsa_capture --real --quiet
```

The default polling interval is 0.05 seconds, plus processing time (about 20 Hz
at most). Use `--interval` to adjust it and `--samples` to limit capture.
Stop with Ctrl+C. Completed event batches are committed during capture, and the
active session is finalized on Ctrl+C or a shared-memory error. This protects
previously committed laps if a later read fails. A force-killed process cannot
finalize the active session; SQL metadata and Parquet files are not a single
atomic transaction.

## API and dashboard

Use separate terminals with the environment activated:

```powershell
python -m uvicorn ac_race_engineer.api.app:create_local_app --factory --host 127.0.0.1 --port 8000
python -m streamlit run src/ac_race_engineer/dashboard/app.py
```

API documentation: <http://127.0.0.1:8000/docs>.
The local factory connects the API to `DATABASE_URL` (or the default PostgreSQL
URL) and disposes its database engine on shutdown. Apply migrations before use.
The **Mis sesiones** workspace lets you select two recorded laps and save the
comparison; **Historial** reopens stored reports. **Importar datos** remains
available for supplied traces. LLM explanations are disabled by default.

For an analysis-only API without database access, the original
`ac_race_engineer.api.app:app` entry point remains available.

## Architecture

| Directory | Responsibility |
| --- | --- |
| `telemetry/assetto_corsa` | Read game memory, track events and compare driving traces |
| `storage` | Record telemetry and write Parquet traces |
| `database` / `migrations` | Relational persistence and schema evolution |
| `analysis` / `services` / `ml` | Dynamics analysis, experiments and predictive models |
| `api` / `dashboard` | Expose analysis and display results |
| `lakehouse` / `spark` / `kafka` | Batch and streaming data engineering workflows |
| `tests` | Automated regression checks |

Kafka and Spark are separate development workflows; they are not required to
start the direct Assetto Corsa capture command. Setup details:
[Kafka](docs/kafka.md), [streaming](docs/streaming.md),
[Spark on Windows](docs/spark-windows.md).

## Validation

```powershell
python -m ruff check src tests
python -m pytest -q
```

Spark tests need a working Java/Spark environment, and tests marked
`kafka_integration` need the external broker and connector. For a quick check of
the direct capture path:

```powershell
python -m pytest -q tests/test_assetto_corsa_capture_runner.py tests/test_assetto_corsa_persistence.py tests/test_database_foundation.py
```

## Next milestones

1. Validate real capture across pauses, pit visits, session changes and game exit.
2. Expand simulated scenarios to cover pauses, pit visits and session changes.
3. Measure capture latency and missed samples before increasing sampling frequency.
4. Add live feedback after validating diagnosis quality on real laps.
5. Document a reproducible driving demonstration and ML evaluation for the portfolio.

## Arranque sencillo en Windows

Con el entorno instalado, abre `iniciar-aplicacion.bat`. El lanzador usa SQLite local e inicia y cierra los dos servicios juntos. Consulta [la guía de primera prueba](docs/primer-arranque.md) para preparar el ordenador con Assetto Corsa.
