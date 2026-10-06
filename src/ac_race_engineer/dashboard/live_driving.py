"""Local live display with explicit connection states and a test source."""
from dataclasses import dataclass
from time import monotonic

import streamlit as st

from ac_race_engineer.dashboard.api_client import RaceEngineerAPIClient, RaceEngineerAPIError
from ac_race_engineer.dashboard.driving import (
    delta_style,
    demo_laps,
    interpolate,
    lap_time,
    reference_time,
    render_pedal,
)
from ac_race_engineer.dashboard.locale_es import api_error_message, friendly_name
from ac_race_engineer.telemetry.assetto_corsa.live_monitor import LiveMonitor
from ac_race_engineer.telemetry.assetto_corsa.mapper import normalize_gear
from ac_race_engineer.telemetry.assetto_corsa.trace import DrivingTraceSample
from ac_race_engineer.telemetry.assetto_corsa.windows_backend import WindowsSharedMemoryBackend

STATES = {"waiting": "Esperando al juego", "live": "En pista", "paused": "En pausa", "disconnected": "Desconectado", "replay": "Repetición del juego"}


@dataclass
class SimulationClock:
    position: float = 0.0
    updated_at: float | None = None
    was_running: bool = False

    def advance(self, now: float, *, running: bool, duration: float) -> float:
        if running and self.was_running and self.updated_at is not None:
            self.position = (self.position + max(0.0, now - self.updated_at)) % duration
        self.updated_at = now
        self.was_running = running
        return self.position


def render_live_driving(client=None):
    simulation_clock = st.session_state.get("live_simulation_clock")
    if simulation_clock:
        simulation_clock.was_running = False
        simulation_clock.updated_at = monotonic()
    st.caption("La conexión lee Assetto Corsa en el mismo ordenador donde se ejecuta esta aplicación.")
    simulated = st.toggle("Probar conexión simulada", value=True)
    if simulated:
        scenario = st.selectbox("Estado que quieres probar", ["En pista", "En pausa", "Esperando al juego", "Desconectado"])
        st.caption("Fuente simulada · No está conectado a Assetto Corsa")
    else:
        scenario = None
        st.caption("Fuente: Assetto Corsa local · Visualización sin guardar la sesión")
    reference = demo_laps()[0] if simulated else _select_reference(client)
    _live_panel(simulated, scenario, reference)


@st.fragment(run_every=0.25)
def _live_panel(simulated, scenario, reference):
    if simulated:
        monitor = st.session_state.pop("live_monitor", None)
        if monitor:
            monitor.close()
        state = {value: key for key, value in STATES.items()}[scenario]
        reading = None
    else:
        if "live_monitor" not in st.session_state:
            st.session_state.live_monitor = LiveMonitor(WindowsSharedMemoryBackend)
        reading = st.session_state.live_monitor.poll()
        state = reading.state
    if simulated:
        if "live_simulation_clock" not in st.session_state:
            st.session_state.live_simulation_clock = SimulationClock()
        elapsed = st.session_state.live_simulation_clock.advance(monotonic(), running=state == "live", duration=demo_laps()[1][-1].elapsed_seconds)
    if state in ("waiting", "disconnected"):
        st.warning(STATES[state])
        st.caption("Abre el juego y entra en una sesión. La aplicación vuelve a intentar la conexión automáticamente cada dos segundos." if not simulated else "Este estado simulado oculta los valores para evitar mostrar telemetría antigua como actual.")
        return
    st.badge(STATES[state] + (" · Simulación" if simulated else " · Juego local"))
    if simulated:
        trace = demo_laps()[1]
        sample = interpolate(trace, elapsed)
        speed, gas, brake, clutch = sample["speed_kmh"], sample["throttle"], sample["brake"], 0.0
        gear = min(6, max(1, int(speed / 35) + 1))
        progress = sample["progress"]
        st.caption("Coche simulado · Marcha estimada · Embrague simulado sin pulsar")
    else:
        physics, graphics = reading.physics, reading.graphics
        speed, gas, brake, clutch = physics.speed_kmh, physics.gas, physics.brake, physics.clutch
        gear, elapsed, progress = normalize_gear(physics.gear_raw), graphics.current_time_ms / 1000, graphics.normalized_car_position
        st.caption(f"{friendly_name(reading.static.car_model)} · {friendly_name(reading.static.track)} · Vuelta {graphics.completed_laps + 1}")
    with st.container(horizontal=True):
        st.metric("Velocidad", f"{speed:.0f} km/h", border=True, width=230)
        st.metric("Marcha", "R" if gear == -1 else "N" if gear == 0 else str(gear), border=True, width=160)
        st.metric("Tiempo de vuelta", lap_time(max(0, elapsed)), border=True, width=230)
    if simulated:
        delta, reason = live_delta(progress, elapsed, reference)
    elif reference:
        ref_session, _ref_number, ref_trace = reference
        same_context = ref_session.get("car_key") == reading.static.car_model and ref_session.get("track_key") == reading.static.track
        delta, reason = live_delta(progress, elapsed, ref_trace, compatible=same_context)
    else:
        delta, reason = None, "Carga una vuelta de referencia para comparar tu tiempo."
    with st.container(border=True):
        st.caption("Diferencia con referencia")
        if delta is None:
            st.markdown("### Sin referencia")
            st.caption(reason)
        else:
            color, status = delta_style(delta)
            st.markdown(f"## :{color}[{delta:+.3f} s]")
            st.caption(status + " · Comparación en el mismo punto del circuito")
    st.progress(max(0.0, min(1.0, progress)), text="Posición en la vuelta")
    for column, (label, value, color) in zip(st.columns(3), (("Acelerador", gas, "#35D78B"), ("Freno", brake, "#FF6577"), ("Embrague", clutch, "#71CFFF")), strict=True):
        with column, st.container(border=True):
            render_pedal(label, max(0.0, min(1.0, value)), color)
    st.caption("Referencia simulada: primera vuelta; conducción simulada: segunda vuelta, más lenta en la primera curva." if simulated else "La comparación usa la vuelta cargada; no valida penalizaciones, condiciones de pista ni vueltas de boxes.")


def live_delta(progress, elapsed, trace, *, compatible=True):
    if not compatible:
        return None, "La referencia pertenece a otro coche o circuito."
    if not trace or len(trace) < 2:
        return None, "No hay suficientes datos en la referencia."
    if not trace[0].progress <= progress <= trace[-1].progress:
        return None, "La referencia no cubre este tramo del circuito."
    return elapsed - reference_time(progress, trace), ""


def _select_reference(client):
    from ac_race_engineer.dashboard.saved_sessions import _laps, _sessions
    if not st.checkbox("Comparar con una vuelta guardada", value=False):
        return None
    client = RaceEngineerAPIClient(client.base_url, timeout_seconds=5) if client else RaceEngineerAPIClient(timeout_seconds=5)
    loaded = None
    with st.expander("Elegir referencia", expanded=True):
        try:
            sessions = _sessions(client.base_url)
            if not sessions:
                st.info("Todavía no hay sesiones guardadas para usar como referencia.")
                return None
            by_id = {item["session_id"]: item for item in sessions}
            session_id = st.selectbox("Sesión de referencia en directo", list(by_id), format_func=lambda key: f"{friendly_name(by_id[key]['car_key'])} · {friendly_name(by_id[key]['track_key'])} · {key[:8]}")
            laps = {lap["lap_number"]: lap for lap in _laps(client.base_url, session_id) if lap["trace_available"]}
            if not laps:
                st.info("Esta sesión no tiene telemetría disponible.")
                return None
            numbers = sorted(laps)
            best = min(numbers, key=lambda number: laps[number]["lap_time_ms"])
            with st.form("live-reference-form"):
                number = st.selectbox("Vuelta de referencia en directo", numbers, index=numbers.index(best))
                submit = st.form_submit_button("Usar como referencia")
            if submit:
                st.session_state.pop("live_reference", None)
                samples = tuple(DrivingTraceSample(**item) for item in client.get_trace(session_id, number)["samples"])
                st.session_state.live_reference = (by_id[session_id], number, samples)
            stored = st.session_state.get("live_reference")
            if stored and stored[0]["session_id"] == session_id:
                loaded = stored
                st.caption(f"Referencia cargada: vuelta {stored[1]} · {lap_time(stored[2][-1].elapsed_seconds)}")
        except RaceEngineerAPIError as exc:
            st.error(api_error_message(exc))
    return loaded
