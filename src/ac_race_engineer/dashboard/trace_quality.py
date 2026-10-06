"""Describe sample coverage without assigning an unsupported confidence score."""
from itertools import pairwise

import streamlit as st


def trace_quality(reference: list[dict], target: list[dict]) -> dict:
    def describe(rows):
        gaps = [(right["progress"] - left["progress"], left["progress"], right["progress"])
                for left, right in pairwise(rows)]
        largest, start, end = max(gaps, default=(0, rows[0]["progress"], rows[0]["progress"]))
        return {"samples": len(rows), "start": rows[0]["progress"], "end": rows[-1]["progress"],
                "largest_gap": largest, "gap_start": start, "gap_end": end}

    ref, lap = describe(reference), describe(target)
    start, end = max(ref["start"], lap["start"]), min(ref["end"], lap["end"])
    return {"reference": ref, "target": lap, "shared_start": start,
            "shared_end": end, "shared_span": max(0.0, end - start)}


def render_trace_quality(reference: list[dict], target: list[dict], *, estimated: bool) -> None:
    quality = trace_quality(reference, target)
    st.subheader("Qué datos estamos comparando")
    st.caption("Tiempos estimados a partir de distancia y velocidad" if estimated else "Tiempos incluidos en los archivos; no se han estimado")
    start, end = quality["shared_start"], quality["shared_end"]
    st.progress(quality["shared_span"], text=f"Tramo compartido: {start:.1%} a {end:.1%} del recorrido")
    st.caption("Esta barra indica el tramo entre los extremos de ambas vueltas, no cuántos puntos se han registrado dentro de él. La escala procede de los archivos y no confirma que se haya completado una vuelta real.")
    for column, label, detail in zip(st.columns(2), ("Referencia", "Tu vuelta"),
                                     (quality["reference"], quality["target"]), strict=True):
        with column, st.container(border=True):
            st.markdown(f"**{label}**")
            st.metric("Muestras registradas", detail["samples"])
            st.caption(f"Mayor separación entre muestras: {detail['largest_gap']:.1%} del recorrido, entre {detail['gap_start']:.1%} y {detail['gap_end']:.1%}.")
    sparse = any(detail["largest_gap"] > 0.05 for detail in (quality["reference"], quality["target"]))
    if sparse:
        st.warning("Hay separaciones de más del 5 % del recorrido entre muestras. En esos tramos se interpolan los datos: puedes pasar por alto frenadas o cambios de acelerador. El 5 % es un aviso orientativo, no una medida de precisión.")
    if start > 0.001 or end < 0.999:
        st.info("La comparación cubre solo el tramo compartido. Fuera de él no se calcula una diferencia con la referencia.")
    with st.expander("Cómo se comparan las vueltas"):
        st.markdown("Las muestras se alinean por **posición en el recorrido**, no por el segundo en que se tomaron. La diferencia de tiempo compara cuánto tarda cada vuelta en llegar a la misma posición. Entre muestras se interpolan valores; añadir puntos al gráfico no añade telemetría real.")
        if estimated:
            st.caption("Sin tiempos registrados, se aproxima cada intervalo mediante la distancia y la velocidad media de sus extremos. Las diferencias y las recomendaciones deben interpretarse como orientativas.")
