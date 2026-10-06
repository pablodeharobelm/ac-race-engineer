from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from ac_race_engineer.dashboard.locale_es import (
    PHASES,
    PRIORITIES,
    coaching_copy,
    format_date,
)
from ac_race_engineer.telemetry.assetto_corsa.trace import (
    AssettoCorsaTraceComparisonService,
    DrivingTraceSample,
)


def _format_seconds(value: object) -> str:
    return f"{value:+.3f} s" if isinstance(value, (int, float)) else "Sin datos"


def render_analysis_summary(analysis: dict[str, Any]) -> None:
    st.subheader("Tu vuelta, de un vistazo")
    metrics = (
        ("Vuelta de referencia", analysis.get("reference_lap_number", "—")),
        ("Vuelta que analizas", analysis.get("target_lap_number", "—")),
        ("Balance en las curvas", _format_seconds(analysis.get("net_time_delta_seconds"))),
        ("Tiempo perdido en curvas", _format_seconds(analysis.get("total_time_lost_seconds"))),
    )
    with st.container(horizontal=True, gap="medium"):
        for label, value in metrics:
            st.metric(label, value, width=215, border=True, delta=value if label in ("Balance en las curvas", "Tiempo perdido en curvas") and value != "Sin datos" else None, delta_color="inverse")
    st.caption("Un valor positivo significa que tardas más que la referencia; uno negativo, que eres más rápido. Estas cifras resumen las curvas detectadas.")


def render_trace_comparison(reference_trace: list[dict[str, Any]], target_trace: list[dict[str, Any]]) -> None:
    if not reference_trace or not target_trace:
        return
    st.subheader("Así cambia tu conducción")
    with st.expander("Centrar el análisis en un tramo"):
        st.button("Ver todo el recorrido", on_click=lambda: st.session_state.update(comparison_range=(0, 100)))
        start, end = st.slider("Tramo del recorrido (%)", 0, 100, (0, 100), key="comparison_range",
                               help="Elige el inicio y el final del tramo. La selección se conserva al cambiar de gráfica.")
        st.caption("Solo cambia la zona visible de la gráfica. Los resultados del análisis y la diferencia acumulada conservan su significado original.")
    if start == end:
        st.info("Separa el inicio y el final para ver un tramo del recorrido.")
        return
    mode = st.segmented_control("Qué quieres comparar", ["Velocidad", "Acelerador", "Freno", "Volante", "Diferencia de tiempo"], default="Velocidad")
    mode = mode or "Velocidad"
    explanations = {
        "Velocidad": "Compara cuánto corres en cada parte de la vuelta. Una caída mayor de la línea roja indica que tu coche pasa más despacio.",
        "Acelerador": "0 % significa pedal suelto; 100 %, acelerador a fondo. Comprueba dónde empiezas a acelerar al salir de cada curva.",
        "Freno": "0 % significa que no frenas; 100 %, frenada máxima. Compara el punto de frenada y cómo vas soltando el pedal.",
        "Volante": "Compara cuánto giras y dónde empiezas a abrir la dirección. Se conserva el signo registrado en los archivos: no se asigna izquierda o derecha. Más giro no significa mejor conducción.",
        "Diferencia de tiempo": "Por encima de cero vas perdiendo tiempo; por debajo, lo ganas. El gráfico muestra la diferencia entre los tiempos transcurridos de ambas vueltas.",
    }
    st.caption(explanations[mode])
    x = alt.X("Posición:Q", title="Posición en la vuelta (%)", scale=alt.Scale(domain=[start, end], nice=False))
    if mode == "Diferencia de tiempo":
        try:
            comparison = AssettoCorsaTraceComparisonService().compare(
                reference_lap_number=1, target_lap_number=2,
                reference_trace=tuple(DrivingTraceSample(**sample) for sample in reference_trace),
                target_trace=tuple(DrivingTraceSample(**sample) for sample in target_trace),
            )
        except ValueError:
            st.info("No hay suficientes puntos comunes para mostrar la diferencia de tiempo.")
            return
        frame = pd.DataFrame([{"Posición": point.progress * 100, "Diferencia": point.time_delta_seconds} for point in comparison.points])
        line = alt.Chart(frame).mark_line(color="#FF6577", strokeWidth=3, clip=True).encode(
            x=x, y=alt.Y("Diferencia:Q", title="Diferencia acumulada (s)"),
            tooltip=[alt.Tooltip("Posición:Q", title="Posición (%)", format=".1f"), alt.Tooltip("Diferencia:Q", title="Diferencia (s)", format="+.3f")],
        )
        zero = alt.Chart(pd.DataFrame({"Cero": [0]})).mark_rule(color="#64748B", strokeDash=[5, 5]).encode(y="Cero:Q")
        chart = line + zero
    else:
        field, unit, multiplier = {"Velocidad": ("speed_kmh", "km/h", 1), "Acelerador": ("throttle", "%", 100), "Freno": ("brake", "%", 100), "Volante": ("steering_angle_deg", "°", 1)}[mode]
        frame = pd.DataFrame([
            {"Posición": sample["progress"] * 100, "Valor": sample[field] * multiplier, "Vuelta": name}
            for trace, name in ((reference_trace, "Referencia"), (target_trace, "Tu vuelta"))
            for sample in trace
        ])
        chart = alt.Chart(frame).mark_line(strokeWidth=3, clip=True).encode(
            x=x, y=alt.Y("Valor:Q", title=f"{mode} ({unit})"),
            color=alt.Color("Vuelta:N", title="Vuelta", scale=alt.Scale(domain=["Referencia", "Tu vuelta"], range=["#71CFFF", {"Acelerador": "#35D78B", "Volante": "#C8A2FF"}.get(mode, "#FF6577")])),
            strokeDash=alt.StrokeDash("Vuelta:N", title="Vuelta", scale=alt.Scale(domain=["Referencia", "Tu vuelta"], range=[[7, 4], [1, 0]])),
            tooltip=[alt.Tooltip("Posición:Q", title="Posición (%)", format=".1f"), alt.Tooltip("Valor:Q", title=f"{mode} ({unit})", format=".1f"), "Vuelta:N"],
        )
        if mode == "Volante":
            zero = alt.Chart(pd.DataFrame({"Cero": [0]})).mark_rule(color="#64748B", strokeDash=[5, 5]).encode(y="Cero:Q")
            chart = chart + zero
    st.altair_chart(chart.properties(height=290), width="stretch")
    if start != 0 or end != 100:
        st.caption(f"Vista ampliada: del {start} % al {end} % del recorrido. Las líneas entre muestras son interpoladas.")
    st.caption("La posición usa la escala del archivo; sus extremos no confirman una vuelta completa. " + ("Azul discontinua: referencia. Línea continua: tu vuelta." if mode != "Diferencia de tiempo" else "La diferencia solo cubre el tramo compartido por ambas vueltas."))


def render_corner_analysis(analysis: dict[str, Any]) -> None:
    corners = analysis.get("corners", [])
    st.subheader("Dónde se te escapa el tiempo")
    if not corners:
        st.info("No se han detectado curvas con datos suficientes para un diagnóstico.")
        return
    rows = [{"Curva": f"Curva {corner['corner_number']}", "Balance": corner.get("time_lost_seconds", 0) - corner.get("time_gained_seconds", 0)} for corner in corners]
    chart = alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusEnd=5).encode(
        x=alt.X("Balance:Q", title="Tiempo perdido (+) o ganado (−), en segundos"),
        y=alt.Y("Curva:N", sort=None, title=None),
        color=alt.condition(alt.datum.Balance > 0, alt.value("#FF6577"), alt.value("#35D78B")),
        tooltip=["Curva:N", alt.Tooltip("Balance:Q", title="Balance (s)", format="+.3f")],
    )
    st.altair_chart(chart.properties(height=max(120, min(450, len(rows) * 45))), width="stretch")
    worst = max(corners, key=lambda item: item.get("time_lost_seconds", 0))
    if worst.get("time_lost_seconds", 0) > 0:
        phase = PHASES.get(worst.get("dominant_phase"), "Paso por la curva").lower()
        st.markdown(f"**Empieza por la curva {worst['corner_number']}.** Pierdes {worst['time_lost_seconds']:.3f} s; la fase con mayor diferencia es: {phase}.")
    with st.expander("Ver el detalle de las curvas"):
        st.caption("Entrada: desde que empiezas a girar hasta el vértice. Vértice: el punto interior de la curva. Salida: desde el vértice hasta volver a acelerar.")
        st.dataframe([{
            "Curva": corner["corner_number"],
            "Tiempo perdido (s)": round(corner.get("time_lost_seconds", 0), 3),
            "Tiempo ganado (s)": round(corner.get("time_gained_seconds", 0), 3),
            "Pérdida en entrada (s)": round(corner.get("entry_time_loss_seconds", 0), 3),
            "Pérdida en salida (s)": round(corner.get("exit_time_loss_seconds", 0), 3),
            "Diferencia de velocidad en vértice (km/h)": round(corner.get("apex_speed_delta_kmh", 0), 1),
        } for corner in corners], hide_index=True, width="stretch")


def render_coaching(analysis: dict[str, Any]) -> None:
    st.subheader("Qué puedes mejorar en la próxima vuelta")
    focuses = analysis.get("focuses", [])
    if not focuses:
        st.caption("No hay una recomendación suficientemente clara con estos datos.")
        return
    for focus in focuses:
        title, instruction, rationale = coaching_copy(focus)
        with st.container(border=True):
            st.markdown(f"### {focus.get('rank', '—')}. {title}")
            priority = PRIORITIES.get(str(focus.get("priority", "")).lower(), "Sin determinar")
            st.caption(f"Curva {focus.get('corner_number', '—')} · Prioridad {priority.lower()}")
            st.write(instruction)
            st.caption(f"Por qué: {rationale}")


def render_ai_explanation(analysis: dict[str, Any]) -> None:
    explanation = analysis.get("explanation")
    if not explanation:
        return
    with st.expander("Explicación del ingeniero con IA", expanded=True):
        if explanation.get("language", "es") != "es":
            st.caption("Este informe se guardó en otro idioma. Genera un análisis nuevo para obtener una explicación en español.")
        elif explanation.get("text"):
            st.markdown(explanation["text"])
            st.caption(f"Basada en {explanation.get('recommendation_count', 0)} recomendaciones y {explanation.get('corner_count', 0)} curvas.")
        else:
            st.caption("No se ha recibido una explicación del servicio de IA.")


def render_history_table(analyses: list[dict[str, Any]]) -> None:
    if not analyses:
        st.info("Todavía no hay análisis guardados.")
        return
    st.caption(f"{len(analyses)} análisis disponibles. Selecciona uno para recuperar sus recomendaciones.")
    with st.expander("Ver el resumen del historial"):
        st.dataframe([{
            "Fecha": format_date(analysis.get("created_at")),
            "Referencia": analysis.get("reference_lap_number"),
            "Vuelta analizada": analysis.get("target_lap_number"),
            "Balance en curvas (s)": round(analysis.get("net_time_delta_seconds", 0), 3),
            "Recomendaciones": analysis.get("recommendations_selected", 0),
        } for analysis in analyses], hide_index=True, width="stretch")
