"""Clock-based demo playback, independent of the analysis API."""
import json
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from time import monotonic

import altair as alt
import pandas as pd
import streamlit as st

from ac_race_engineer.dashboard.api_client import RaceEngineerAPIClient, RaceEngineerAPIError
from ac_race_engineer.dashboard.locale_es import api_error_message, friendly_name
from ac_race_engineer.telemetry.assetto_corsa.demo_backend import build_demo_trace
from ac_race_engineer.telemetry.assetto_corsa.trace import DrivingTraceSample


@lru_cache(maxsize=1)
def demo_laps():
    return build_demo_trace(slower=False), build_demo_trace(slower=True)


@dataclass
class Playback:
    position: float = 0.0
    playing: bool = False
    updated_at: float = 0.0
    rate: float = 1.0

    def advance(self, now: float, duration: float) -> None:
        if self.playing:
            self.position = min(duration, self.position + max(0.0, now - self.updated_at) * self.rate)
        self.updated_at = now
        if self.position >= duration:
            self.playing = False


def interpolate(trace, elapsed: float):
    index = min(len(trace) - 2, max(0, bisect_right([p.elapsed_seconds for p in trace], elapsed) - 1))
    left, right = trace[index:index + 2]
    ratio = max(0.0, min(1.0, (elapsed - left.elapsed_seconds) / (right.elapsed_seconds - left.elapsed_seconds)))
    values = {field: getattr(left, field) + ratio * (getattr(right, field) - getattr(left, field))
            for field in ("progress", "speed_kmh", "throttle", "brake", "steering_angle_deg")}
    values["gear"] = right.gear if ratio >= 1 else left.gear
    values["clutch"] = left.clutch + ratio * (right.clutch - left.clutch) if left.clutch is not None and right.clutch is not None else None
    return values


def reference_time(progress: float, trace=None) -> float:
    trace = trace or demo_laps()[0]
    index = min(len(trace) - 2, max(0, bisect_right([point.progress for point in trace], progress) - 1))
    left, right = trace[index:index + 2]
    ratio = (progress - left.progress) / (right.progress - left.progress) if right.progress > left.progress else 0.0
    return left.elapsed_seconds + ratio * (right.elapsed_seconds - left.elapsed_seconds)


def lap_time(seconds: float) -> str:
    minutes, remainder = divmod(round(seconds * 1000), 60000)
    return f"{minutes}:{remainder / 1000:06.3f}"


def render_driving(client: RaceEngineerAPIClient | None = None) -> None:
    st.header("Modo conducción")
    source = st.segmented_control("Qué quieres reproducir", ["Demostración", "Vueltas guardadas", "Vueltas importadas", "En directo"], default="Demostración", key="driving_source")
    if source != st.session_state.get("previous_driving_source"):
        playback = st.session_state.get("driving_playback")
        if playback:
            playback.playing = False
        st.session_state.previous_driving_source = source
    if source == "En directo":
        from ac_race_engineer.dashboard.live_driving import render_live_driving
        render_live_driving(client)
        return
    monitor = st.session_state.pop("live_monitor", None)
    if monitor:
        monitor.close()
    replay_label = "Vuelta guardada"
    if source == "Vueltas importadas":
        imported = st.session_state.get("imported_analysis")
        if imported is None:
            st.info("Primero compara tus dos JSON en Importar datos. Después podrás reproducir aquí la vuelta analizada.")
            return
        analysis, reference_rows, target_rows = imported
        reference = tuple(DrivingTraceSample(**item) for item in reference_rows)
        target = tuple(DrivingTraceSample(**item) for item in target_rows)
        source_id = "imported:" + sha256(json.dumps([reference_rows, target_rows], sort_keys=True).encode()).hexdigest()
        replay_label = "Vuelta importada"
        st.caption("Reproducción de tus JSON · Misma referencia que en el análisis · Sin conexión al juego")
        if analysis.get("time_estimated"):
            st.warning("Tiempos y diferencias aproximados, calculados a partir de distancia y velocidad. Los huecos entre muestras reducen la precisión.")
    elif source != "Vueltas guardadas":
        source_id = "demo"
        reference, target = demo_laps()
        st.caption("Demostración simulada · Dos vueltas · Sin conexión al juego")
    else:
        from ac_race_engineer.dashboard.saved_sessions import _laps, _sessions
        client = RaceEngineerAPIClient(client.base_url, timeout_seconds=5) if client else RaceEngineerAPIClient(timeout_seconds=5)
        try:
            sessions = _sessions(client.base_url)
            if not sessions:
                st.info("Todavía no hay sesiones guardadas. Puedes probar la demostración.")
                return
            by_id = {item["session_id"]: item for item in sessions}
            session_id = st.selectbox("Sesión para reproducir", list(by_id), format_func=lambda key: f"{friendly_name(by_id[key]['car_key'])} · {friendly_name(by_id[key]['track_key'])} · {key[:8]}")
            available = {lap["lap_number"]: lap for lap in _laps(client.base_url, session_id) if lap["trace_available"]}
            if not available:
                st.info("Esta sesión no tiene vueltas con telemetría disponible.")
                return
            numbers = sorted(available)
            best = min(numbers, key=lambda number: available[number]["lap_time_ms"])
            with st.form("load-driving-replay"):
                ref_number = st.selectbox("Referencia para la reproducción", numbers, index=numbers.index(best))
                target_number = st.selectbox("Vuelta para reproducir", numbers, index=len(numbers) - 1)
                submitted = st.form_submit_button("Cargar vuelta", type="primary")
            if submitted:
                st.session_state.replay_source_id = None
                st.session_state.pop("recorded_replay", None)
                with st.spinner("Cargando la telemetría…"):
                    reference = tuple(DrivingTraceSample(**item) for item in client.get_trace(session_id, ref_number)["samples"])
                    target = tuple(DrivingTraceSample(**item) for item in client.get_trace(session_id, target_number)["samples"])
                st.session_state.recorded_replay = (session_id, ref_number, target_number, reference, target)
            saved = st.session_state.get("recorded_replay")
            if not saved or saved[0] != session_id:
                st.info("Selecciona tus vueltas y pulsa Cargar vuelta.")
                return
            _, ref_number, target_number, reference, target = saved
            source_id = f"{session_id}:{ref_number}:{target_number}"
            st.caption(f"Reproducción de la vuelta {target_number} · Referencia: vuelta {ref_number} · Datos guardados, sin conexión en directo al juego")
            st.caption("Las sesiones antiguas pueden no incluir marcha o embrague; esos indicadores muestran Sin datos.")
        except RaceEngineerAPIError as exc:
            st.error(api_error_message(exc))
            return
    if st.session_state.get("replay_source_id") != source_id:
        st.session_state.driving_playback = Playback(updated_at=monotonic())
        st.session_state.pop("driving_seek", None)
        st.session_state.replay_source_id = source_id
    _render_playback(reference, target, source_id == "demo", replay_label)


def _toggle_playback() -> None:
    playback = st.session_state.driving_playback
    playback.advance(monotonic(), st.session_state.get("replay_duration", sum(lap[-1].elapsed_seconds for lap in demo_laps())))
    playback.playing = not playback.playing


def _reset_playback() -> None:
    st.session_state.driving_playback = Playback(updated_at=monotonic(), rate=st.session_state.get("driving_rate", 1.0))
    st.session_state.driving_seek = 0.0


def _seek_playback() -> None:
    playback = st.session_state.driving_playback
    playback.position = st.session_state.driving_seek
    playback.playing = False
    playback.updated_at = monotonic()


@st.fragment(run_every=0.25)
def _render_playback(reference, target, demo: bool, replay_label: str = "Vuelta guardada") -> None:
    duration = reference[-1].elapsed_seconds + target[-1].elapsed_seconds if demo else target[-1].elapsed_seconds - target[0].elapsed_seconds
    st.session_state.replay_duration = duration
    if "driving_playback" not in st.session_state:
        st.session_state.driving_playback = Playback(updated_at=monotonic())
    playback = st.session_state.driving_playback
    playback.advance(monotonic(), duration)
    with st.container(horizontal=True):
        st.button("Pausar" if playback.playing else "Reproducir", type="primary", disabled=playback.position >= duration, on_click=_toggle_playback)
        st.button("Reiniciar", on_click=_reset_playback)
        rate = st.selectbox("Velocidad de reproducción", [1.0, 2.0, 4.0], format_func=lambda value: f"{value:g}×", key="driving_rate")
        playback.rate = rate
    with st.expander("Buscar un momento de la vuelta"):
        st.slider("Saltar a un momento (segundos)", 0.0, float(duration), 0.0, key="driving_seek", on_change=_seek_playback,
                  help="Al moverlo, la reproducción salta a ese momento y queda en pausa para revisar los pedales.")
    second_lap = demo and playback.position >= reference[-1].elapsed_seconds
    elapsed = playback.position - reference[-1].elapsed_seconds if second_lap else playback.position
    if not demo:
        elapsed += target[0].elapsed_seconds
    sample = interpolate(target if second_lap or not demo else reference, elapsed)
    delta = elapsed - reference_time(sample["progress"], reference) if reference[0].progress <= sample["progress"] <= reference[-1].progress else None
    if playback.position >= duration:
        st.success("Reproducción terminada. Reinicia para volver a verla.")
    else:
        st.badge(("Reproduciendo" if playback.playing else "En pausa") + (" · Simulación" if demo else f" · {replay_label}"), icon=":material/sports_motorsports:")
    primary, timing = st.columns([1.4, 1])
    with primary, st.container(border=True):
        speed_column, gear_column = st.columns([2, 1])
        with speed_column:
            st.metric("Velocidad", f"{sample['speed_kmh']:.0f} km/h")
        with gear_column:
            gear = sample["gear"]
            gear_text = "Sin datos" if gear is None else "R" if gear == -1 else "N" if gear == 0 else str(gear)
            st.metric("Marcha estimada" if demo else "Marcha", str(min(6, max(1, int(sample['speed_kmh'] / 35) + 1))) if demo else gear_text)
        st.progress(sample["progress"], text=(f"Vuelta {2 if second_lap else 1} de 2 · " if demo else f"{replay_label} · ") + f"{sample['progress'] * 100:.0f} % del recorrido")
    with timing, st.container(border=True):
        st.metric("Tiempo de vuelta", lap_time(elapsed))
        color, status = delta_style(delta) if delta is not None else ("gray", "Fuera de la zona compartida con la referencia")
        st.caption("Diferencia con referencia")
        st.markdown(f"## :{color}[{delta:+.3f} s]" if delta is not None else "## Sin referencia")
        st.caption(status)
    pedal_columns = st.columns(3)
    for column, (label, value, color) in zip(pedal_columns, (
        ("Acelerador", sample["throttle"], "#35D78B"),
        ("Freno", sample["brake"], "#FF6577"),
        ("Embrague", sample["clutch"], "#71CFFF"),
    ), strict=True):
        with column, st.container(border=True):
            render_pedal(label, value, color)
    with st.container(border=True):
        st.subheader("Cómo estás girando")
        steering, baseline = st.columns(2)
        with steering:
            st.metric("Ángulo de tu volante", f"{sample['steering_angle_deg']:+.1f}°")
        with baseline:
            reference_angle = interpolate(reference, reference_time(sample["progress"], reference))["steering_angle_deg"] if delta is not None else None
            st.metric("Volante de referencia", "Sin referencia" if reference_angle is None else f"{reference_angle:+.1f}°")
        st.caption("Ángulos comparados en la misma posición del recorrido. El signo se conserva del archivo; no se asigna izquierda o derecha sin conocer su convención. Más giro no significa mejor conducción.")
    st.caption(f"Referencia: {lap_time(reference[-1].elapsed_seconds)}" + (f" · Última vuelta: {lap_time(reference[-1].elapsed_seconds) if second_lap else 'Todavía sin completar'}" if demo else f" · {replay_label}"))
    with st.expander("Cómo interpretar el panel"):
        st.markdown("**Verde:** ganas tiempo. **Rojo:** pierdes tiempo. **Gris:** al mismo ritmo. La diferencia compara ambas vueltas en el mismo punto del recorrido.")
        st.caption("En la demostración la marcha es estimada. En vueltas guardadas se usa la marcha registrada: N significa punto muerto y R, marcha atrás. Los indicadores sin telemetría muestran Sin datos. Los colores de los pedales identifican cada control, no valoran tu conducción.")


def delta_style(delta: float) -> tuple[str, str]:
    if delta > 0.0005:
        return "red", "Pierdes tiempo"
    if delta < -0.0005:
        return "green", "Ganas tiempo"
    return "gray", "Al mismo ritmo"


def render_pedal(label: str, value: float | None, color: str) -> None:
    text_color = {"Acelerador": "green", "Freno": "red", "Embrague": "blue"}[label]
    st.markdown(f"**:{text_color}[{label}]**")
    st.subheader("Sin datos" if value is None else f"{value * 100:.0f} %")
    frame = pd.DataFrame({"Valor": [0.0 if value is None else value * 100], "Máximo": [100]})
    background = alt.Chart(frame).mark_bar(color="#29384B", cornerRadius=5, size=16).encode(
        x=alt.X("Máximo:Q", scale=alt.Scale(domain=[0, 100]), axis=None),
    )
    filled = alt.Chart(frame).mark_bar(color=color, cornerRadius=5, size=16).encode(
        x=alt.X("Valor:Q", scale=alt.Scale(domain=[0, 100]), axis=None),
    )
    st.altair_chart((background + filled).properties(height=22).configure_view(stroke=None), width="stretch")
    if value is None:
        st.caption(":blue[Embrague · pendiente de telemetría]")
