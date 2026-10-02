from typing import Any

import pandas as pd
import streamlit as st


def render_analysis_summary(
    analysis: dict[str, Any],
) -> None:
    st.subheader(
        "Session overview"
    )

    columns = st.columns(
        5
    )

    columns[0].metric(
        "Reference lap",
        analysis.get(
            "reference_lap_number",
            "-",
        ),
    )

    columns[1].metric(
        "Target lap",
        analysis.get(
            "target_lap_number",
            "-",
        ),
    )

    columns[2].metric(
        "Net delta",
        _format_seconds(
            analysis.get(
                "net_time_delta_seconds"
            )
        ),
    )

    columns[3].metric(
        "Time lost",
        _format_seconds(
            analysis.get(
                "total_time_lost_seconds"
            )
        ),
    )

    columns[4].metric(
        "Trend",
        str(
            analysis.get(
                "trend",
                "-",
            )
        ).replace(
            "_",
            " ",
        ).title(),
    )


def render_trace_comparison(
    reference_trace: list[
        dict[str, Any]
    ],
    target_trace: list[
        dict[str, Any]
    ],
) -> None:
    if (
        not reference_trace
        or not target_trace
    ):
        return

    st.subheader(
        "Lap comparison"
    )

    reference_frame = _trace_frame(
        reference_trace,
        "Reference",
    )

    target_frame = _trace_frame(
        target_trace,
        "Target",
    )

    combined = pd.concat(
        [
            reference_frame,
            target_frame,
        ],
        ignore_index=True,
    )

    speed = combined.pivot_table(
        index="progress",
        columns="lap",
        values="speed_kmh",
    )

    st.caption(
        "Speed comparison"
    )

    st.line_chart(
        speed
    )

    throttle = combined.pivot_table(
        index="progress",
        columns="lap",
        values="throttle",
    )

    st.caption(
        "Throttle"
    )

    st.line_chart(
        throttle
    )

    brake = combined.pivot_table(
        index="progress",
        columns="lap",
        values="brake",
    )

    st.caption(
        "Brake"
    )

    st.line_chart(
        brake
    )


def render_corner_analysis(
    analysis: dict[str, Any],
) -> None:
    st.subheader(
        "Corner analysis"
    )

    corners = analysis.get(
        "corners",
        [],
    )

    if not corners:
        st.info(
            "No corner-level diagnostics were generated."
        )
        return

    frame = pd.DataFrame(
        corners
    )

    preferred_columns = [
        "corner_number",
        "time_lost_seconds",
        "time_gained_seconds",
        "entry_time_loss_seconds",
        "exit_time_loss_seconds",
        "dominant_phase",
        "minimum_speed_delta_kmh",
        "apex_speed_delta_kmh",
        "exit_speed_delta_kmh",
        "issue_count",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in frame.columns
    ]

    st.dataframe(
        frame[
            available_columns
        ],
        width="stretch",
        hide_index=True,
    )


def render_coaching(
    analysis: dict[str, Any],
) -> None:
    st.subheader(
        "Coaching priorities"
    )

    focuses = analysis.get(
        "focuses",
        [],
    )

    if not focuses:
        st.info(
            "No coaching priorities were selected."
        )
        return

    for focus in focuses:
        rank = focus.get(
            "rank",
            "-",
        )

        title = focus.get(
            "title",
            "Coaching focus",
        )

        corner = focus.get(
            "corner_number",
            "-",
        )

        priority = str(
            focus.get(
                "priority",
                "",
            )
        ).upper()

        with st.container(
            border=True
        ):
            st.markdown(
                f"### #{rank} · {title}"
            )

            st.caption(
                f"Corner {corner} · Priority {priority}"
            )

            instruction = focus.get(
                "instruction"
            )

            if instruction:
                st.write(
                    instruction
                )

            rationale = focus.get(
                "rationale"
            )

            if rationale:
                st.caption(
                    rationale
                )


def render_ai_explanation(
    analysis: dict[str, Any],
) -> None:
    st.subheader(
        "AI Race Engineer"
    )

    explanation = analysis.get(
        "explanation"
    )

    if not explanation:
        st.info(
            "No LLM explanation was requested."
        )
        return

    text = explanation.get(
        "text"
    )

    if not text:
        st.info(
            "The LLM returned no explanation."
        )
        return

    st.markdown(
        text
    )

    recommendation_count = (
        explanation.get(
            "recommendation_count",
            0,
        )
    )

    corner_count = explanation.get(
        "corner_count",
        0,
    )

    st.caption(
        "Grounded from "
        f"{recommendation_count} recommendations "
        f"across {corner_count} corners."
    )


def render_history_table(
    analyses: list[
        dict[str, Any]
    ],
) -> None:
    if not analyses:
        st.info(
            "No persisted analyses found."
        )
        return

    rows = []

    for analysis in analyses:
        rows.append(
            {
                "analysis_id": (
                    analysis.get(
                        "analysis_id"
                    )
                ),
                "session_id": (
                    analysis.get(
                        "session_id"
                    )
                ),
                "reference_lap": (
                    analysis.get(
                        "reference_lap_number"
                    )
                ),
                "target_lap": (
                    analysis.get(
                        "target_lap_number"
                    )
                ),
                "trend": (
                    analysis.get(
                        "trend"
                    )
                ),
                "net_delta_s": (
                    analysis.get(
                        "net_time_delta_seconds"
                    )
                ),
                "time_lost_s": (
                    analysis.get(
                        "total_time_lost_seconds"
                    )
                ),
                "recommendations": (
                    analysis.get(
                        "recommendations_selected"
                    )
                ),
                "created_at": (
                    analysis.get(
                        "created_at"
                    )
                ),
            }
        )

    st.dataframe(
        pd.DataFrame(
            rows
        ),
        width="stretch",
        hide_index=True,
    )


def _trace_frame(
    trace: list[
        dict[str, Any]
    ],
    lap_name: str,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        trace
    ).copy()

    frame[
        "lap"
    ] = lap_name

    return frame


def _format_seconds(
    value: object,
) -> str:
    if not isinstance(
        value,
        (int, float),
    ):
        return "-"

    return f"{value:+.3f} s"