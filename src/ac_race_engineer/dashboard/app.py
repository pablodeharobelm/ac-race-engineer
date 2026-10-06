import json
import os
from typing import Any

import streamlit as st

from ac_race_engineer.dashboard.api_client import (
    RaceEngineerAPIClient,
    RaceEngineerAPIError,
)
from ac_race_engineer.dashboard.components import (
    render_ai_explanation,
    render_analysis_summary,
    render_coaching,
    render_corner_analysis,
    render_history_table,
    render_trace_comparison,
)
from ac_race_engineer.dashboard.driving import render_driving
from ac_race_engineer.dashboard.locale_es import api_error_message, format_date, friendly_name
from ac_race_engineer.dashboard.report_export import render_report_download
from ac_race_engineer.dashboard.saved_sessions import render_saved_sessions
from ac_race_engineer.dashboard.trace_quality import render_trace_quality
from ac_race_engineer.dashboard.trace_transfer import (
    distance_extent,
    ensure_same_context,
    needs_estimated_time,
    normalize_distance_rows,
    sample_rows,
    uploaded_text,
)

DEFAULT_REFERENCE_TRACE = [
    {
        "progress": 0.0,
        "elapsed_seconds": 0.0,
        "speed_kmh": 120.0,
        "throttle": 1.0,
        "brake": 0.0,
        "steering_angle_deg": 0.0,
    },
    {
        "progress": 0.5,
        "elapsed_seconds": 50.0,
        "speed_kmh": 80.0,
        "throttle": 0.2,
        "brake": 0.7,
        "steering_angle_deg": 18.0,
    },
    {
        "progress": 1.0,
        "elapsed_seconds": 100.0,
        "speed_kmh": 130.0,
        "throttle": 1.0,
        "brake": 0.0,
        "steering_angle_deg": 0.0,
    },
]


DEFAULT_TARGET_TRACE = [
    {
        "progress": 0.0,
        "elapsed_seconds": 0.0,
        "speed_kmh": 118.0,
        "throttle": 1.0,
        "brake": 0.0,
        "steering_angle_deg": 0.0,
    },
    {
        "progress": 0.5,
        "elapsed_seconds": 51.0,
        "speed_kmh": 75.0,
        "throttle": 0.1,
        "brake": 0.8,
        "steering_angle_deg": 20.0,
    },
    {
        "progress": 1.0,
        "elapsed_seconds": 101.0,
        "speed_kmh": 128.0,
        "throttle": 1.0,
        "brake": 0.0,
        "steering_angle_deg": 0.0,
    },
]


def main() -> None:
    st.set_page_config(
        page_title="AC Race Engineer",
        page_icon="🏁",
        layout="wide",
    )

    st.title(
        "Tu ingeniero de pista"
    )

    st.caption(
        "Entiende tu conducción, encuentra dónde pierdes tiempo "
        "y mejora vuelta a vuelta."
    )

    with st.sidebar:
        st.subheader("AC Race Engineer")
        st.caption("Telemetría que te ayuda a conducir mejor.")
        with st.expander("Imágenes del juego"):
            st.text_input(
                "Carpeta de Assetto Corsa", value=os.getenv("ASSETTO_CORSA_PATH", ""),
                key="assetto_corsa_path", placeholder="Carpeta donde está instalado el juego",
            )
            st.caption("En el ordenador con el juego, indica su carpeta para mostrar sus imágenes. Aquí usamos ilustraciones provisionales.")
    client = _build_client()

    page = st.segmented_control(
        "Tu espacio", ["Mis sesiones", "Conducción", "Historial", "Importar datos"], default="Mis sesiones",
    )
    page = page or "Mis sesiones"
    if page == "Conducción":
        render_driving(client)
        return
    monitor = st.session_state.pop("live_monitor", None)
    if monitor:
        monitor.close()
    playback = st.session_state.get("driving_playback")
    if playback is not None:
        playback.playing = False
    _render_connection_status(client)
    if page == "Mis sesiones":
        render_saved_sessions(client)
    elif page == "Importar datos":
        _render_analysis_page(
            client
        )
    elif page == "Historial":
        _render_history_page(
            client
        )


def _build_client(
) -> RaceEngineerAPIClient:
    base_url = os.getenv(
        "RACE_ENGINEER_API_URL",
        "http://127.0.0.1:8000",
    )

    return RaceEngineerAPIClient(
        base_url=base_url
    )


def _render_connection_status(
    client: RaceEngineerAPIClient,
) -> None:
    try:
        health = client.health()

    except RaceEngineerAPIError:
        st.error(
            "El servicio de análisis no está disponible. Inícialo para consultar tus sesiones."
        )
        return

    status = health.get(
        "status",
        "unknown",
    )

    if status == "ok":
        st.success(
            "Servicio de análisis conectado.",
            icon="✅",
        )

    else:
        st.warning(
            "El servicio de análisis no está listo."
        )


def _render_analysis_page(
    client: RaceEngineerAPIClient,
) -> None:
    st.header(
        "Comparar datos importados"
    )
    st.caption("Carga dos vueltas en JSON: exportadas desde Mis sesiones o con distancia en metros y pedales en porcentaje. La importación analiza los archivos; no añade una sesión al catálogo.")
    input_mode = st.segmented_control("Cómo quieres cargar las vueltas", ["Archivos", "Datos de ejemplo", "Pegar JSON"], default="Archivos", key="import_mode")

    settings_column, persistence_column = (
        st.columns(
            2
        )
    )

    with settings_column:
        reference_lap_number = st.number_input(
            "Vuelta de referencia",
            min_value=1,
            value=1,
            step=1,
        )

        target_lap_number = st.number_input(
            "Vuelta que analizas",
            min_value=1,
            value=2,
            step=1,
        )

        grid_points = st.number_input(
            "Precisión de la comparación",
            min_value=2,
            max_value=5001,
            value=201,
            step=1,
        )

        explain = st.checkbox(
            "Añadir explicación con IA",
            value=False,
        )

    with persistence_column:
        persist = st.checkbox(
            "Guardar en el historial",
            value=False,
        )

        session_id = st.text_input(
            "Identificador de sesión",
            value="",
            disabled=not persist,
            placeholder="Opcional",
        )

        language = "es"

    trace_column_a, trace_column_b = (
        st.columns(
            2
        )
    )

    reference_text = json.dumps(DEFAULT_REFERENCE_TRACE)
    target_text = json.dumps(DEFAULT_TARGET_TRACE)
    reference_upload = target_upload = None
    if input_mode == "Archivos":
        with trace_column_a:
            reference_upload = st.file_uploader("Archivo de la vuelta de referencia", type=["json"], max_upload_size=20, key="reference_upload")
        with trace_column_b:
            target_upload = st.file_uploader("Archivo de la vuelta que analizas", type=["json"], max_upload_size=20, key="target_upload")
    elif input_mode == "Pegar JSON":
        with trace_column_a:
            reference_text = st.text_area("Datos de la referencia (JSON)", value=json.dumps(DEFAULT_REFERENCE_TRACE, indent=2), height=250)
        with trace_column_b:
            target_text = st.text_area("Datos de tu vuelta (JSON)", value=json.dumps(DEFAULT_TARGET_TRACE, indent=2), height=250)
    else:
        st.info("Compararás dos vueltas de ejemplo. Estos datos son simulados.")

    estimate_times = st.checkbox("Permitir tiempos estimados", value=False, help="Para archivos sin tiempos: calcula una aproximación a partir de distancia y velocidad. No equivale a telemetría cronometrada.")
    if st.button(
        "Comparar vueltas",
        disabled=input_mode == "Archivos" and (reference_upload is None or target_upload is None),
        type="primary",
        width="stretch",
    ):
        st.session_state.pop("imported_analysis", None)

        try:
            if input_mode == "Archivos":
                reference_text, target_text = uploaded_text(reference_upload), uploaded_text(target_upload)
            track_length = distance_extent(reference_text, target_text)
            reference_trace = _parse_trace(
                reference_text,
                label="los datos de referencia", allow_estimated_time=estimate_times, track_length=track_length,
            )

            target_trace = _parse_trace(
                target_text,
                label="los datos de tu vuelta", allow_estimated_time=estimate_times, track_length=track_length,
            )

            if input_mode == "Archivos":
                ensure_same_context(reference_text, target_text)
            time_estimated = needs_estimated_time(reference_text, target_text)

        except (ValueError, TypeError, KeyError) as exc:
            st.error(str(exc))
            return

        payload: dict[str, Any] = {
            "reference_lap_number": int(
                reference_lap_number
            ),
            "target_lap_number": int(
                target_lap_number
            ),
            "reference_trace": (
                reference_trace
            ),
            "target_trace": (
                target_trace
            ),
            "grid_points": int(
                grid_points
            ),
            "explain": explain,
            "language": language,
            "persist": persist and not time_estimated,
            "session_id": (
                session_id.strip()
                if persist
                and session_id.strip()
                else None
            ),
        }

        try:
            with st.spinner(
                "Analizando las vueltas…"
            ):
                analysis = client.analyze(
                    payload
                )

        except RaceEngineerAPIError as exc:
            st.error(api_error_message(exc))
            return

        analysis["time_estimated"] = time_estimated
        st.session_state["imported_analysis"] = (analysis, reference_trace, target_trace)

    saved = st.session_state.get("imported_analysis")
    if saved is None:
        return
    analysis, reference_trace, target_trace = saved
    if analysis.get("time_estimated"):
        st.warning("Tiempos aproximados calculados a partir de distancia y velocidad. Los huecos entre muestras reducen la precisión. Este análisis no se guarda en el historial.")

    st.success(
        "Análisis completado."
    )

    analysis_id = analysis.get(
        "analysis_id"
    )

    if analysis_id:
        st.caption(
            "Análisis guardado en el historial."
        )

    render_report_download(analysis, key="download-import-report", reference_trace=reference_trace, target_trace=target_trace)
    render_trace_quality(reference_trace, target_trace, estimated=bool(analysis.get("time_estimated")))
    render_analysis_summary(
        analysis
    )

    render_trace_comparison(
        reference_trace,
        target_trace,
    )

    render_corner_analysis(
        analysis
    )

    render_coaching(
        analysis
    )

    render_ai_explanation(
        analysis
    )


def _render_history_page(
    client: RaceEngineerAPIClient,
) -> None:
    st.header(
        "Tus análisis guardados"
    )

    mode = st.radio(
        "Qué quieres consultar",
        options=[
            "Últimos análisis",
            "Por sesión",
        ],
        horizontal=True,
    )

    try:
        if mode == "Últimos análisis":
            limit = st.slider(
                "Número máximo de análisis",
                min_value=1,
                max_value=100,
                value=20,
            )

            analyses = client.list_recent(
                limit=limit
            )

        else:
            sessions = client.list_sessions(limit=100)
            if not sessions:
                st.info("Todavía no hay sesiones registradas.")
                return
            session_labels = {
                session["session_id"]: (
                    f"{friendly_name(session['car_key'])} · {friendly_name(session['track_key'])} · "
                    f"{session['session_id'][:8]}"
                )
                for session in sessions
            }
            session_id = st.selectbox(
                "Sesión que quieres consultar", list(session_labels), format_func=session_labels.get,
                key="history-session-id",
            )

            analyses = (
                client.list_for_session(
                    session_id
                )
            )

    except RaceEngineerAPIError as exc:
        st.error(api_error_message(exc))
        return

    render_history_table(
        analyses
    )

    if not analyses:
        return

    options = {analysis["analysis_id"]: analysis for analysis in analyses if analysis.get("analysis_id")}
    if not options:
        return

    def analysis_label(analysis_id: str) -> str:
        analysis = options[analysis_id]
        return (
            f"{format_date(analysis.get('created_at'))} · "
            f"Vueltas {analysis.get('reference_lap_number')} → {analysis.get('target_lap_number')}"
        )

    selected_id = st.selectbox(
        "Abrir un análisis guardado", list(options), format_func=analysis_label,
    )

    try:
        selected = client.get_analysis(
            selected_id
        )

    except RaceEngineerAPIError as exc:
        st.error(api_error_message(exc))
        return


    render_report_download(selected, key="download-history-report")
    render_analysis_summary(
        selected
    )

    report = selected.get(
        "report",
        {}
    )

    if isinstance(
        report,
        dict,
    ):
        render_corner_analysis(
            report
        )

        render_coaching(
            report
        )

    explanation = selected.get(
        "explanation"
    )

    if explanation is not None:
        render_ai_explanation(
            {
                "explanation": explanation,
            }
        )


def _parse_trace(
    text: str,
    *,
    label: str,
    allow_estimated_time: bool = False,
    track_length: float | None = None,
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(
            text
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"No se puede leer {label}: revisa la línea {exc.lineno} y la columna {exc.colno}."
        ) from exc

    payload = sample_rows(payload)
    if not isinstance(
        payload,
        list,
    ):
        raise TypeError(
            f"{label} debe contener una lista de muestras."
        )

    if len(
        payload
    ) < 2:
        raise ValueError(
            f"{label} debe incluir al menos dos muestras."
        )

    for index, sample in enumerate(
        payload
    ):
        if not isinstance(
            sample,
            dict,
        ):
            raise TypeError(
                f"La muestra {index + 1} de {label} debe ser un objeto de datos."
            )

    try:
        payload, _estimated = normalize_distance_rows(payload, allow_estimated_time=allow_estimated_time, track_length=track_length)
    except (KeyError, TypeError) as exc:
        raise ValueError("El archivo contiene muestras incompletas de distancia, velocidad o pedales.") from exc
    from pydantic import ValidationError

    from ac_race_engineer.api.schemas import DrivingTraceSampleRequest
    for index, sample in enumerate(payload):
        try:
            DrivingTraceSampleRequest.model_validate(sample)
        except ValidationError as exc:
            raise ValueError(f"La muestra {index + 1} de {label} contiene datos incompletos o fuera de rango.") from exc
    return payload


if __name__ == "__main__":
    main()
