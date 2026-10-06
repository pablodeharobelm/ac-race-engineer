"""Session pace summaries using recorded lap times, without loading traces."""
from dataclasses import dataclass
from statistics import mean, pstdev

import altair as alt
import pandas as pd
import streamlit as st

from ac_race_engineer.telemetry.assetto_corsa.history import format_time_ms


@dataclass(frozen=True)
class PaceSummary:
    laps: tuple[tuple[int, int], ...]
    best_number: int
    best_ms: int
    average_ms: float
    spread_ms: float | None
    change_ms: int | None


def summarize_pace(laps: list[dict]) -> PaceSummary | None:
    recorded = tuple(sorted((lap["lap_number"], lap["lap_time_ms"]) for lap in laps if lap["lap_time_ms"] > 0))
    if not recorded:
        return None
    times = [time for _, time in recorded]
    best_number, best_ms = min(recorded, key=lambda pair: pair[1])
    return PaceSummary(recorded, best_number, best_ms, mean(times),
                       pstdev(times) if len(times) >= 3 else None,
                       times[-1] - times[-2] if len(times) >= 2 else None)


def render_session_progress(laps: list[dict]) -> None:
    st.subheader("Tu evolución en esta sesión")
    summary = summarize_pace(laps)
    if summary is None:
        st.info("Todavía no hay tiempos de vuelta disponibles para mostrar tu evolución.")
        return
    with st.container(horizontal=True):
        st.metric("Tu mejor vuelta", format_time_ms(summary.best_ms), border=True, width=220)
        st.metric("Ritmo medio", format_time_ms(round(summary.average_ms)), border=True, width=220)
        st.metric("Última vuelta", format_time_ms(summary.laps[-1][1]),
                  delta=f"{summary.change_ms / 1000:+.3f} s" if summary.change_ms is not None else None,
                  delta_color="inverse", border=True, width=220)
    if summary.change_ms is not None:
        change = summary.change_ms
        if change == 0:
            st.markdown("La última vuelta iguala el tiempo de la anterior.")
        else:
            color, direction = ("green", "más rápida") if change < 0 else ("red", "más lenta")
            st.markdown(f"La última vuelta ha sido **:{color}[{abs(change) / 1000:.3f} s {direction}]** que la anterior registrada.")
    if summary.spread_ms is None:
        st.caption("Con tres vueltas cronometradas empezaremos a medir tu regularidad. Con pocas vueltas, las conclusiones son provisionales.")
    else:
        st.caption(f"Variación de tus tiempos: {summary.spread_ms / 1000:.3f} s. Cuanto menor sea, más parecidas son tus vueltas; esta cifra es la desviación estándar de los tiempos registrados.")
    frame = pd.DataFrame([
        {"Vuelta": number, "Tiempo": time / 1000, "Respecto a tu mejor": (time - summary.best_ms) / 1000,
         "Tiempo de vuelta": format_time_ms(time)}
        for number, time in summary.laps
    ])
    mode = st.segmented_control("Ver evolución por", ["Tiempo de vuelta", "Distancia a tu mejor vuelta"], default="Tiempo de vuelta", key="pace_view")
    field = "Respecto a tu mejor" if mode == "Distancia a tu mejor vuelta" else "Tiempo"
    chart = alt.Chart(frame).mark_line(point=True, color="#71CFFF", strokeWidth=3).encode(
        x=alt.X("Vuelta:Q", axis=alt.Axis(tickMinStep=1), title="Número de vuelta"),
        y=alt.Y(f"{field}:Q", title="Segundos respecto a tu mejor vuelta" if field != "Tiempo" else "Tiempo de vuelta (s)", scale=alt.Scale(zero=False)),
        tooltip=["Vuelta:Q", "Tiempo de vuelta:N", alt.Tooltip("Respecto a tu mejor:Q", title="Diferencia con tu mejor (s)", format="+.3f")],
    )
    st.altair_chart(chart.properties(height=220), width="stretch")
    st.caption(f"Mejor tiempo: vuelta {summary.best_number}. Se incluyen las vueltas con tiempo registrado, aunque su telemetría no esté disponible. No se filtran vueltas de boxes ni penalizaciones: aún no disponemos de esa información.")
