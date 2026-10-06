"""Saved-session workflow; the API owns all database and Parquet access."""

from typing import Any

import streamlit as st

from ac_race_engineer.dashboard.api_client import RaceEngineerAPIClient, RaceEngineerAPIError
from ac_race_engineer.dashboard.components import (
    render_ai_explanation,
    render_analysis_summary,
    render_coaching,
    render_corner_analysis,
    render_trace_comparison,
)
from ac_race_engineer.dashboard.locale_es import api_error_message, format_date, friendly_name
from ac_race_engineer.dashboard.report_export import render_report_download
from ac_race_engineer.dashboard.session_progress import render_session_progress
from ac_race_engineer.dashboard.session_visuals import render_session_identity
from ac_race_engineer.dashboard.trace_transfer import trace_file
from ac_race_engineer.telemetry.assetto_corsa.history import format_time_ms


@st.cache_data(ttl=5, max_entries=10)
def _sessions(base_url: str) -> list[dict[str, Any]]:
    return RaceEngineerAPIClient(base_url, timeout_seconds=5).list_sessions(limit=100)


@st.cache_data(ttl=5, max_entries=30)
def _laps(base_url: str, session_id: str) -> list[dict[str, Any]]:
    return RaceEngineerAPIClient(base_url, timeout_seconds=5).list_laps(session_id)


def render_saved_sessions(client: RaceEngineerAPIClient) -> None:
    st.header("Comparar mis vueltas")
    st.caption("Elige una sesión y descubre cómo mejorar tu siguiente vuelta.")
    if st.button("Actualizar sesiones", icon=":material/refresh:"):
        _sessions.clear()
        _laps.clear()
    try:
        sessions = _sessions(client.base_url)
    except RaceEngineerAPIError as exc:
        st.error(api_error_message(exc))
        return
    if not sessions:
        st.info("Todavía no tienes sesiones. Registra una sesión o ejecuta la demostración de dos vueltas.")
        return
    by_id = {session["session_id"]: session for session in sessions}

    def session_label(session_id: str) -> str:
        session = by_id[session_id]
        date = session.get("started_at") or session["created_at"]
        return (
            f"{friendly_name(session['car_key'])} · {friendly_name(session['track_key'])} · "
            f"{format_date(date)} · {session['lap_count']} vueltas · {session_id[:8]}"
        )

    session_id = st.selectbox(
        "Tu sesión", list(by_id), format_func=session_label, key="captured-session",
    )
    render_session_identity(by_id[session_id])
    try:
        laps = _laps(client.base_url, session_id)
    except RaceEngineerAPIError as exc:
        st.error(api_error_message(exc))
        return
    if not laps:
        st.info("Esta sesión aún no tiene vueltas completas. Actualiza la lista después de terminar una vuelta.")
        return
    render_session_progress(laps)
    with st.expander("Ver todas las vueltas y sus datos"):
        st.caption("Solo las vueltas con telemetría disponible pueden compararse.")
        st.dataframe([
            {"Vuelta": lap["lap_number"], "Tiempo": format_time_ms(lap["lap_time_ms"]),
             "Muestras registradas": lap["sample_count"],
             "Telemetría": "Disponible" if lap["trace_available"] else "No disponible o incompleta"}
            for lap in laps
        ], hide_index=True, width="stretch")
    available = {lap["lap_number"]: lap for lap in laps if lap["trace_available"]}
    if len(available) < 2:
        st.info("Necesitas dos vueltas con telemetría completa para comparar.")
        return

    def lap_label(number: int) -> str:
        return f"Vuelta {number} · {format_time_ms(available[number]['lap_time_ms'])}"

    numbers = list(available)
    best = min(numbers, key=lambda number: available[number]["lap_time_ms"])
    with st.form(f"compare-saved-laps-{session_id}"):
        reference = st.selectbox("Vuelta de referencia", numbers, index=numbers.index(best), format_func=lap_label)
        target = st.selectbox("Vuelta que analizas", numbers, index=numbers.index(next(n for n in numbers if n != best)), format_func=lap_label)
        persist = st.checkbox("Guardar en el historial", value=True)
        explain = st.checkbox("Añadir explicación con IA", value=False)
        language = "es"
        submitted = st.form_submit_button("Comparar mis vueltas", type="primary", width="stretch")

    result_key = f"saved-comparison:{client.base_url}:{session_id}"
    if submitted:
        st.session_state.pop("saved_comparison", None)
        if reference == target:
            st.error("Selecciona dos vueltas distintas.")
        else:
            try:
                with st.spinner("Comparando tus vueltas…"):
                    reference_trace = client.get_trace(session_id, reference)["samples"]
                    target_trace = client.get_trace(session_id, target)["samples"]
                    analysis = client.analyze_session(session_id, {
                        "reference_lap_number": reference, "target_lap_number": target,
                        "persist": persist, "explain": explain, "language": language,
                    })
                # Keep only the latest comparison to bound memory across session selections.
                st.session_state["saved_comparison"] = (
                    result_key, analysis, reference_trace, target_trace,
                )
            except RaceEngineerAPIError as exc:
                st.error(api_error_message(exc))

    stored = st.session_state.get("saved_comparison")
    if stored and stored[0] == result_key:
        _, analysis, reference_trace, target_trace = stored
        st.success("Análisis completado.")
        if analysis.get("analysis_id"):
            st.caption("Guardado en tu historial.")
        reference_lap = available.get(analysis["reference_lap_number"])
        target_lap = available.get(analysis["target_lap_number"])
        if reference_lap and target_lap:
            delta = (target_lap["lap_time_ms"] - reference_lap["lap_time_ms"]) / 1000
            st.metric("Diferencia total de la vuelta", f"{delta:+.3f} s")
        st.caption("La diferencia total mide toda la vuelta; el análisis de curvas se centra en las zonas detectadas.")
        render_report_download(analysis, by_id[session_id], key="download-session-report", reference_trace=reference_trace, target_trace=target_trace)
        with st.expander("Llevar estas vueltas a otro ordenador"):
            st.caption("Descarga los dos archivos y cárgalos en Importar datos. Conservan las muestras, incluida marcha y embrague cuando están disponibles.")
            st.download_button("Descargar vuelta de referencia", trace_file(reference_trace, lap_number=analysis["reference_lap_number"], session=by_id[session_id]), file_name=f"referencia-vuelta-{analysis['reference_lap_number']}.json", mime="application/json", key="export-reference-trace", on_click="ignore")
            st.download_button("Descargar vuelta analizada", trace_file(target_trace, lap_number=analysis["target_lap_number"], session=by_id[session_id]), file_name=f"analizada-vuelta-{analysis['target_lap_number']}.json", mime="application/json", key="export-target-trace", on_click="ignore")
        render_analysis_summary(analysis)
        render_coaching(analysis)
        render_corner_analysis(analysis)
        render_trace_comparison(reference_trace, target_trace)
        render_ai_explanation(analysis)
