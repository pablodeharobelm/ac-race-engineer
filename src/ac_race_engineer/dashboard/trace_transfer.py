"""Portable lap files; importing compares samples without creating a session."""
import json


def trace_file(samples: list[dict], *, lap_number: int, session: dict) -> str:
    return json.dumps({"format": "ac-race-engineer-lap", "version": 1,
                       "lap_number": lap_number, "car_key": session.get("car_key"),
                       "track_key": session.get("track_key"), "samples": samples},
                      ensure_ascii=False, allow_nan=False, indent=2)


def uploaded_text(upload) -> str:
    if upload.size > 20 * 1024 * 1024:
        raise ValueError("El archivo supera el límite de 20 MB.")
    try:
        return upload.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("No se puede leer el archivo. Usa una vuelta exportada por la aplicación.") from exc


def ensure_same_context(reference_text: str, target_text: str) -> None:
    reference, target = json.loads(reference_text), json.loads(target_text)
    if not isinstance(reference, dict) or not isinstance(target, dict):
        return
    for field, label in (("car_key", "coche"), ("track_key", "circuito")):
        if reference.get(field) and target.get(field) and reference[field] != target[field]:
            raise ValueError(f"Los archivos pertenecen a distinto {label}. Elige dos vueltas del mismo coche y circuito.")


def sample_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if payload.get("format") and (payload["format"] != "ac-race-engineer-lap" or payload.get("version") != 1):
            raise ValueError("El formato o la versión del archivo no es compatible.")
        if "samples" in payload:
            return payload["samples"]
        lists = [value for value in payload.values() if isinstance(value, list)]
        if len(lists) == 1:
            return lists[0]
    return None


def distance_extent(*texts):
    distances = []
    for text in texts:
        try:
            rows = sample_rows(json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError("El archivo no contiene un JSON válido. Revisa su contenido.") from exc
        if isinstance(rows, list):
            distances.extend(row["lap_distance_m"] for row in rows if isinstance(row, dict) and "lap_distance_m" in row)
    from math import isfinite
    if any(not isinstance(value, (int, float)) or not isfinite(value) or value < 0 for value in distances):
        raise ValueError("Las distancias deben ser números válidos y positivos o cero.")
    return max(distances) if distances else None


def needs_estimated_time(*texts):
    return any(isinstance(row, dict) and "lap_distance_m" in row and "elapsed_seconds" not in row
               for text in texts for row in (sample_rows(json.loads(text)) or []))


def normalize_distance_rows(rows, *, allow_estimated_time=False, track_length=None):
    from math import isfinite
    if not rows or "lap_distance_m" not in rows[0]:
        return rows, False
    length = track_length or max(row["lap_distance_m"] for row in rows)
    if not isinstance(length, (int, float)) or not isfinite(length) or length <= 0:
        raise ValueError("La distancia del recorrido debe ser positiva.")
    estimated = any("elapsed_seconds" not in row for row in rows)
    if estimated and not allow_estimated_time:
        raise ValueError("Estos archivos no incluyen tiempos. Activa Permitir tiempos estimados para comparar de forma aproximada.")
    result = []
    elapsed = 0.0
    previous = None
    for row in rows:
        distance, speed = row["lap_distance_m"], row["speed_kmh"]
        if not all(isinstance(value, (int, float)) and isfinite(value) for value in (distance, speed)) or distance < 0 or speed < 0:
            raise ValueError("La distancia y la velocidad deben ser válidas; no se pueden estimar tiempos con velocidad cero.")
        if previous is not None:
            if distance <= previous[0]:
                raise ValueError("Las distancias deben aumentar en cada muestra.")
            if estimated:
                mean_speed = (speed + previous[1]) / 2 / 3.6
                if mean_speed <= 0:
                    raise ValueError("No se pueden estimar tiempos entre dos muestras con velocidad cero.")
                elapsed += (distance - previous[0]) / mean_speed
        sample = {"progress": distance / length, "elapsed_seconds": elapsed if estimated else row["elapsed_seconds"],
                  "speed_kmh": speed, "throttle": row["throttle_pct"] / 100 if "throttle_pct" in row else row["throttle"],
                  "brake": row["brake_pct"] / 100 if "brake_pct" in row else row["brake"],
                  "steering_angle_deg": row.get("steering_angle_deg", row.get("steering_deg"))}
        for field in ("gear", "clutch"):
            if field in row:
                sample[field] = row[field]
        result.append(sample)
        previous = distance, speed
    return result, estimated
