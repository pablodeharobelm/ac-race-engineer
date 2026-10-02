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
        "🏁 AC Race Engineer"
    )

    st.caption(
        "Telemetry analysis, coaching and AI-assisted "
        "race engineering for Assetto Corsa."
    )

    client = _build_client()

    _render_connection_status(
        client
    )

    analysis_tab, history_tab = st.tabs(
        [
            "New analysis",
            "History",
        ]
    )

    with analysis_tab:
        _render_analysis_page(
            client
        )

    with history_tab:
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
            "Race Engineer API is unavailable."
        )
        return

    status = health.get(
        "status",
        "unknown",
    )

    if status == "ok":
        st.success(
            "Race Engineer API connected.",
            icon="✅",
        )

    else:
        st.warning(
            f"API status: {status}"
        )


def _render_analysis_page(
    client: RaceEngineerAPIClient,
) -> None:
    st.header(
        "Analyze two laps"
    )

    settings_column, persistence_column = (
        st.columns(
            2
        )
    )

    with settings_column:
        reference_lap_number = st.number_input(
            "Reference lap",
            min_value=1,
            value=1,
            step=1,
        )

        target_lap_number = st.number_input(
            "Target lap",
            min_value=1,
            value=2,
            step=1,
        )

        grid_points = st.number_input(
            "Grid points",
            min_value=2,
            max_value=5001,
            value=201,
            step=1,
        )

        explain = st.checkbox(
            "Generate AI Race Engineer explanation",
            value=True,
        )

    with persistence_column:
        persist = st.checkbox(
            "Persist analysis",
            value=False,
        )

        session_id = st.text_input(
            "Session ID",
            value="",
            disabled=not persist,
            placeholder="optional-session-id",
        )

        language = st.selectbox(
            "Explanation language",
            options=[
                "es",
                "en",
            ],
            index=0,
        )

    trace_column_a, trace_column_b = (
        st.columns(
            2
        )
    )

    with trace_column_a:
        st.subheader(
            "Reference trace"
        )

        reference_text = st.text_area(
            "Reference trace JSON",
            value=json.dumps(
                DEFAULT_REFERENCE_TRACE,
                indent=2,
            ),
            height=380,
            label_visibility="collapsed",
        )

    with trace_column_b:
        st.subheader(
            "Target trace"
        )

        target_text = st.text_area(
            "Target trace JSON",
            value=json.dumps(
                DEFAULT_TARGET_TRACE,
                indent=2,
            ),
            height=380,
            label_visibility="collapsed",
        )

    if not st.button(
        "Analyze laps",
        type="primary",
        use_container_width=True,
    ):
        return

    try:
        reference_trace = _parse_trace(
            reference_text,
            label="reference trace",
        )

        target_trace = _parse_trace(
            target_text,
            label="target trace",
        )

    except (ValueError, TypeError) as exc:
        st.error(
            str(
                exc
            )
        )
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
        "persist": persist,
        "session_id": (
            session_id.strip()
            if persist
            and session_id.strip()
            else None
        ),
    }

    try:
        with st.spinner(
            "Running Race Engineer analysis..."
        ):
            analysis = client.analyze(
                payload
            )

    except RaceEngineerAPIError as exc:
        st.error(
            str(
                exc
            )
        )
        return

    st.success(
        "Analysis completed."
    )

    analysis_id = analysis.get(
        "analysis_id"
    )

    if analysis_id:
        st.caption(
            f"Persisted analysis: {analysis_id}"
        )

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
        "Analysis history"
    )

    mode = st.radio(
        "History source",
        options=[
            "Recent analyses",
            "Session",
        ],
        horizontal=True,
    )

    try:
        if mode == "Recent analyses":
            limit = st.slider(
                "Maximum analyses",
                min_value=1,
                max_value=100,
                value=20,
            )

            analyses = client.list_recent(
                limit=limit
            )

        else:
            session_id = st.text_input(
                "Session ID to inspect",
                key="history-session-id",
            )

            if not session_id.strip():
                st.info(
                    "Enter a session ID."
                )
                return

            analyses = (
                client.list_for_session(
                    session_id
                )
            )

    except RaceEngineerAPIError as exc:
        st.error(
            str(
                exc
            )
        )
        return

    render_history_table(
        analyses
    )

    if not analyses:
        return

    options = {
        (
            f"{analysis.get('analysis_id')} "
            f"| laps "
            f"{analysis.get('reference_lap_number')}"
            " → "
            f"{analysis.get('target_lap_number')}"
        ): analysis.get(
            "analysis_id"
        )
        for analysis in analyses
        if analysis.get(
            "analysis_id"
        )
    }

    if not options:
        return

    selected_label = st.selectbox(
        "Open persisted analysis",
        options=list(
            options
        ),
    )

    selected_id = options[
        selected_label
    ]

    try:
        selected = client.get_analysis(
            selected_id
        )

    except RaceEngineerAPIError as exc:
        st.error(
            str(
                exc
            )
        )
        return

    st.divider()

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
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(
            text
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {label}: {exc.msg}"
        ) from exc

    if not isinstance(
        payload,
        list,
    ):
        raise TypeError(
            f"{label} must be a JSON array"
        )

    if len(
        payload
    ) < 2:
        raise ValueError(
            f"{label} must contain at least two samples"
        )

    for index, sample in enumerate(
        payload
    ):
        if not isinstance(
            sample,
            dict,
        ):
            raise TypeError(
                f"{label} sample {index} must be an object"
            )

    return payload


if __name__ == "__main__":
    main()