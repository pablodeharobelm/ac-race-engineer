"""Start and stop only the local services owned by this launcher."""
import argparse
import os
import socket
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from threading import Event, Thread
from urllib.error import URLError
from urllib.request import urlopen


def check_port(port: int) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


def stop_process(process) -> None:
    if process.poll() is None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_ready(url, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Un servicio se ha detenido. Revisa los archivos de data/logs.")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.2)
    raise RuntimeError("El servicio no ha arrancado a tiempo. Revisa data/logs.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Iniciar AC Race Engineer en este ordenador")
    parser.add_argument("--demo", action="store_true", help="Añadir una sesión simulada al catálogo local")
    parser.add_argument("--demo-laps", type=int, choices=range(2, 21), default=6, help="Vueltas de la sesión simulada")
    parser.add_argument("--check", action="store_true", help="Comprobar configuración sin iniciar servicios")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--panel-port", type=int, default=8501)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "src/ac_race_engineer/dashboard/app.py"
    if not dashboard.is_file():
        parser.error("Ejecuta este lanzador desde una copia del proyecto.")
    if args.api_port == args.panel_port or any(not 1024 <= port <= 65535 for port in (args.api_port, args.panel_port)):
        parser.error("Los servicios necesitan dos puertos distintos entre 1024 y 65535.")
    import streamlit  # noqa: F401
    import uvicorn  # noqa: F401

    from ac_race_engineer.database.base import Base
    from ac_race_engineer.database.race_engineer_analyses import race_engineer_analysis_metadata
    from ac_race_engineer.database.session import create_database_engine
    from ac_race_engineer.demo_session import capture_demo_session
    print("Configuración correcta: Python, aplicación y dependencias disponibles.")
    print("El juego debe estar en este ordenador para usar la lectura en directo.")
    if args.check:
        return 0
    for port in (args.api_port, args.panel_port):
        try:
            check_port(port)
        except OSError:
            print(f"El puerto {port} está ocupado. Cierra el arranque anterior o elige otros puertos.")
            return 1
    data = root / "data"
    data.mkdir(exist_ok=True)
    database_url = "sqlite+pysqlite:///" + (data / "local.sqlite").as_posix()
    env = dict(os.environ, DATABASE_URL=database_url, RACE_ENGINEER_API_URL=f"http://127.0.0.1:{args.api_port}", PYTHONUTF8="1")
    engine = create_database_engine(database_url)
    try:
        Base.metadata.create_all(engine)
        race_engineer_analysis_metadata.create_all(engine)
        if args.demo:
            capture_demo_session(engine, trace_directory=data / "silver/lap_traces", lap_count=args.demo_laps)
            print("Sesión simulada añadida. Las sesiones anteriores se conservan.")
    finally:
        engine.dispose()
    logs = data / "logs"
    logs.mkdir(exist_ok=True)
    commands = [
        ([sys.executable, "-m", "uvicorn", "ac_race_engineer.api.app:create_local_app", "--factory", "--host", "127.0.0.1", "--port", str(args.api_port)], "api.log", f"http://127.0.0.1:{args.api_port}/health"),
        ([sys.executable, "-m", "streamlit", "run", str(dashboard), "--server.address", "127.0.0.1", "--server.port", str(args.panel_port), "--server.headless", "true", "--browser.gatherUsageStats", "false"], "panel.log", f"http://127.0.0.1:{args.panel_port}/_stcore/health"),
    ]
    processes = []
    try:
        with ExitStack() as stack:
            for command, filename, health in commands:
                logfile = stack.enter_context((logs / filename).open("a", encoding="utf-8"))
                process = subprocess.Popen(command, cwd=root, env=env, stdout=logfile, stderr=subprocess.STDOUT,
                                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                processes.append(process)
                stack.callback(stop_process, process)
                wait_ready(health, process)
            print(f"Abre http://127.0.0.1:{args.panel_port}")
            print("Para cerrar, escribe salir y pulsa Intro, o pulsa Ctrl+C.")
            stop_requested = Event()
            def read_stop():
                try:
                    while input().strip().lower() != "salir":
                        pass
                    stop_requested.set()
                except (EOFError, OSError):
                    pass
            Thread(target=read_stop, daemon=True).start()
            print("Datos locales: data/local.sqlite. No cierres esta ventana mientras uses la aplicación.")
            while all(process.poll() is None for process in processes):
                if stop_requested.wait(0.5):
                    print("Servicios detenidos. Tus sesiones se conservan.")
                    return 0
            raise RuntimeError("Uno de los servicios se ha detenido. Revisa data/logs.")
    except KeyboardInterrupt:
        print("Servicios detenidos. Tus sesiones se conservan.")
        return 0
    except (RuntimeError, OSError) as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
