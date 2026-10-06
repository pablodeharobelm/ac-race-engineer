"""Portable, escaped HTML reports that work without the application."""
from html import escape
from typing import Any

import streamlit as st

from ac_race_engineer.dashboard.locale_es import (
    PRIORITIES,
    coaching_copy,
    format_date,
    friendly_name,
)
from ac_race_engineer.dashboard.report_traces import trace_report_section


def report_html(analysis: dict[str, Any], session: dict | None = None, *, reference_trace=None, target_trace=None) -> str:
    report = analysis.get("report") or analysis
    esc = lambda value: escape(str(value), quote=True)
    identity = "Datos importados o sesión sin identificar"
    if session:
        identity = f"{friendly_name(session.get('car_key'))} · {friendly_name(session.get('track_key'))}"
    if analysis.get("time_estimated"):
        identity += " · Tiempos estimados a partir de distancia y velocidad; resultado aproximado"
    date = format_date(analysis.get("created_at")) if analysis.get("created_at") else "Análisis de la sesión seleccionada"
    net = report.get("net_time_delta_seconds")
    balance = f"{net:+.3f} s" if isinstance(net, (int, float)) else "Sin datos"
    cards = []
    for focus in report.get("focuses", []):
        title, instruction, rationale = coaching_copy(focus)
        priority = PRIORITIES.get(str(focus.get("priority", "")).lower(), "Sin determinar")
        cards.append(f"<article><h3>{esc(title)}</h3><p class='muted'>Curva {esc(focus.get('corner_number', '—'))} · Prioridad {esc(priority.lower())}</p><p>{esc(instruction)}</p><p class='muted'>Por qué: {esc(rationale)}</p></article>")
    rows = []
    for corner in report.get("corners", []):
        delta = corner.get("time_lost_seconds", 0) - corner.get("time_gained_seconds", 0)
        color = "loss" if delta > 0 else "gain" if delta < 0 else ""
        rows.append(f"<tr><th scope='row'>Curva {esc(corner['corner_number'])}</th><td class='{color}'>{delta:+.3f} s</td></tr>")
    advice = "".join(cards) or "<p>No hay una recomendación suficientemente clara con estos datos.</p>"
    corners = "<table><thead><tr><th>Zona</th><th>Tiempo perdido (+) o ganado (−)</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>" if rows else "<p>No se han detectado curvas con datos suficientes.</p>"
    explanation = analysis.get("explanation")
    ai = ""
    if isinstance(explanation, dict) and explanation.get("language", "es") == "es" and explanation.get("text"):
        ai = "<section><h2>Explicación con IA</h2><p class='explanation'>" + esc(explanation["text"]) + "</p></section>"
    trace_section = trace_report_section(reference_trace, target_trace)
    ai = trace_section + ai
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Informe de conducción · AC Race Engineer</title>
<style>
body{{margin:0;background:#0b1018;color:#eaf1fa;font:16px/1.6 system-ui,sans-serif}}main{{max-width:900px;margin:auto;padding:40px 24px}}h1{{font-size:2.5rem;line-height:1.15}}h2{{margin-top:32px}}.muted{{color:#b3c1d1}}.metrics{{display:flex;flex-wrap:wrap;gap:16px}}article,.metric{{background:#141e2b;border:1px solid #29384b;border-radius:14px;padding:20px;margin:12px 0}}.metric strong{{display:block;font-size:1.8rem}}.loss{{color:#ff8896}}.gain{{color:#55e5a0}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #29384b}}.explanation{{white-space:pre-wrap}}footer{{margin-top:40px;font-size:.85rem;color:#b3c1d1}}@media print{{body{{background:white;color:#17283b}}article,.metric{{background:white;border-color:#aaa;break-inside:avoid}}.muted,footer{{color:#465569}}.loss{{color:#a81932}}.gain{{color:#087944}}main{{padding:0}}}}
</style></head><body><main><p class="muted">AC Race Engineer · Informe de telemetría</p><h1>Tu análisis de conducción</h1><p>{esc(identity)}</p><p class="muted">{esc(date)}</p><div class="metrics"><div class="metric">Vuelta de referencia<strong>{esc(report.get('reference_lap_number', analysis.get('reference_lap_number', '—')))}</strong></div><div class="metric">Vuelta analizada<strong>{esc(report.get('target_lap_number', analysis.get('target_lap_number', '—')))}</strong></div><div class="metric">Balance en curvas<strong>{esc(balance)}</strong></div></div><p class="muted">El balance resume las curvas detectadas, no la diferencia total de la vuelta. Positivo: pierdes tiempo. Negativo: lo ganas.</p><section><h2>Qué mejorar en la próxima vuelta</h2>{advice}</section><section><h2>Dónde cambia tu tiempo</h2>{corners}</section>{ai}<footer>Informe basado en las muestras disponibles. Las curvas son zonas detectadas por el análisis; su numeración puede diferir de la oficial del circuito. Puedes imprimir este documento o guardarlo como PDF desde tu navegador.</footer></main></body></html>"""


def render_report_download(analysis: dict[str, Any], session: dict | None = None, *, key: str, reference_trace=None, target_trace=None) -> None:
    st.download_button("Descargar informe", data=report_html(analysis, session, reference_trace=reference_trace, target_trace=target_trace),
                       file_name="informe-conduccion.html", mime="text/html", key=key,
                       icon=":material/download:", on_click="ignore")
    st.caption("Se abre en cualquier navegador. Puedes imprimirlo o guardarlo como PDF.")
