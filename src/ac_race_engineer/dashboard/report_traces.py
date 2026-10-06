"""Self-contained SVG charts for portable telemetry reports."""
from ac_race_engineer.dashboard.trace_quality import trace_quality


def trace_report_section(reference, target) -> str:
    if not reference or not target:
        return ""
    quality = trace_quality(reference, target)
    details = []
    for label, key in (("Referencia", "reference"), ("Tu vuelta", "target")):
        detail = quality[key]
        details.append(f"<p><strong>{label}:</strong> {detail['samples']} muestras. Mayor separación: {detail['largest_gap']:.1%} del recorrido, entre {detail['gap_start']:.1%} y {detail['gap_end']:.1%}.</p>")
    charts = []
    for field, title, unit, pedal_color in (("speed_kmh", "Velocidad", "km/h", None),
                                           ("throttle", "Acelerador", "%", "#35d78b"),
                                           ("brake", "Freno", "%", "#ff6577")):
        scale = 1 if field == "speed_kmh" else 100
        ceiling = max(1, max(row[field] for row in reference + target)) if scale == 1 else 1
        paths = []
        for rows, color, dashed in ((reference, "#71cfff", True), (target, pedal_color or "#ff8896", False)):
            points = " ".join(f"{50 + row['progress'] * 680:.2f},{180 - row[field] / ceiling * 145:.2f}" for row in rows)
            paths.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" stroke-dasharray="{"7 4" if dashed else "none"}"/>')
        charts.append(f'<h3>{title}</h3><svg viewBox="0 0 760 220" role="img" aria-label="{title}: referencia y vuelta analizada" style="width:100%;height:auto"><rect x="50" y="35" width="680" height="145" fill="#141e2b"/><path d="M50 35V180H730" fill="none" stroke="#b3c1d1"/><g fill="#b3c1d1" font-size="14"><text x="0" y="40">{ceiling * scale:.0f}</text><text x="18" y="180">0</text><text x="50" y="205">0 %</text><text x="675" y="205">100 %</text><text x="70" y="24">{unit}</text></g>{"".join(paths)}</svg>')
    return (f"<section><h2>Qué datos estamos comparando</h2><p>Tramo compartido: {quality['shared_start']:.1%} a {quality['shared_end']:.1%} de la escala del recorrido.</p>"
            + "".join(details) + "<p class='muted'>La cobertura describe los extremos de los archivos; no confirma una vuelta completa. Entre muestras se interpolan valores: las separaciones grandes pueden ocultar cambios de conducción.</p>"
            + "<h2>Velocidad y pedales</h2><p>Línea azul discontinua: referencia. Línea continua: tu vuelta. Acelerador verde y freno rojo. Eje horizontal: posición en el recorrido.</p>"
            + "".join(charts) + "</section>")
