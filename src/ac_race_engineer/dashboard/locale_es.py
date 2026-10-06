"""Spanish presentation copy; domain identifiers and stored reports stay stable."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TRENDS = {"losing_time": "Pierdes tiempo", "gaining_time": "Ganas tiempo", "similar": "Ritmo similar", "balanced": "Ritmo similar", "mixed": "Resultado mixto"}
PHASES = {"entry": "Entrada", "exit": "Salida", "apex": "Paso por el vértice", "braking": "Frenada", "unknown": "Sin determinar"}
PRIORITIES = {"high": "Alta", "medium": "Media", "low": "Baja"}

# Copy follows each deterministic recommendation, including historical reports.
COACHING = {
    "Brake slightly later": ("Frena un poco más tarde", "Retrasa ligeramente el inicio de la frenada, manteniendo una entrada estable.", "Empiezas a frenar antes que en la vuelta de referencia y pierdes tiempo en esta curva."),
    "Brake slightly earlier": ("Frena un poco antes", "Adelanta ligeramente la frenada para controlar mejor el coche antes de girar.", "Frenas más tarde que en la referencia y pierdes tiempo al pasar por la curva."),
    "Carry more minimum speed": ("Conserva más velocidad en la curva", "Evita decelerar más de lo necesario en la parte más lenta de la curva.", "Tu velocidad mínima es inferior a la de la vuelta de referencia."),
    "Release the brake earlier": ("Suelta el freno antes", "Empieza a reducir el freno antes y suéltalo progresivamente al acercarte al giro.", "Mantienes la frenada durante más tiempo que en la referencia."),
    "Reduce brake pressure": ("Reduce la intensidad de la frenada", "Aplica menos freno cuando sea posible y busca una deceleración más suave.", "Frenas con más intensidad que en la referencia en una zona donde pierdes tiempo."),
    "Delay turn-in slightly": ("Empieza a girar un poco después", "Espera un poco más antes de empezar a mover el volante.", "Inicias el giro antes que en la vuelta de referencia."),
    "Turn in slightly earlier": ("Empieza a girar un poco antes", "Inicia el giro ligeramente antes, manteniendo el control de la entrada.", "Inicias el giro más tarde que en la referencia."),
    "Reduce entry speed loss": ("Conserva velocidad al entrar", "Evita seguir frenando innecesariamente entre el inicio del giro y el vértice.", "Pierdes más velocidad entre la entrada y el vértice que en la referencia."),
    "Reduce brake carried into turn-in": ("Suelta el freno mientras giras", "Reduce progresivamente el freno a medida que aumentas el giro del volante.", "Mantienes más freno al entrar en la curva que en la referencia."),
    "Reduce steering input": ("Suaviza el giro del volante", "Evita girar más de lo necesario y mueve el volante de forma progresiva.", "Usas más ángulo de volante que en la referencia durante la entrada."),
    "Improve apex speed": ("Mejora la velocidad en el vértice", "Conserva más velocidad en el punto interior de la curva sin perder estabilidad.", "Llegas al vértice con menos velocidad que en la vuelta de referencia."),
    "Apply throttle earlier": ("Acelera antes", "Empieza a acelerar progresivamente cuando el coche esté estable y puedas abrir la dirección.", "Empiezas a acelerar más tarde que en la referencia."),
    "Prioritize exit speed": ("Prioriza la velocidad de salida", "Mantén la aceleración desde el vértice para salir de la curva con más velocidad.", "Sales de la curva más despacio que en la referencia."),
    "Increase exit throttle": ("Aprovecha más el acelerador al salir", "Aumenta el acelerador progresivamente mientras reduces el giro, según permita el agarre.", "Usas menos acelerador al salir que en la referencia."),
    "Unwind steering sooner": ("Abre antes la dirección", "Reduce progresivamente el giro al salir para poder acelerar antes.", "Mantienes más ángulo de volante durante la salida que en la referencia."),
}


def coaching_copy(focus: dict[str, Any]) -> tuple[str, str, str]:
    return COACHING.get(str(focus.get("title", "")), (
        "Revisa tu paso por esta curva",
        "Compara la velocidad y los pedales con la vuelta de referencia.",
        "El análisis ha detectado una diferencia de conducción en esta zona.",
    ))


def friendly_name(key: str | None) -> str:
    if not key:
        return "Sin identificar"
    known = {"ks_mazda_mx5_cup": "Mazda MX-5 Cup", "mazda_mx5_cup": "Mazda MX-5 Cup", "magione": "Magione"}
    return known.get(key, key.removeprefix("ks_").replace("_", " ").title())


def format_date(value: str | None) -> str:
    if not value:
        return "Fecha no disponible"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # SQLite strips timezone information from the UTC capture timestamps.
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo("UTC"))
        return date.astimezone(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y · %H:%M")
    except ValueError:
        return "Fecha no disponible"


def api_error_message(error: Exception) -> str:
    message = str(error).lower()
    if "llm" in message or "explanation_service" in message:
        return "La explicación con IA no está disponible. Configura el servicio de IA o compara sin esa opción."
    if "409" in message or "trace" in message:
        return "No se pueden leer los datos de esa vuelta. Puede faltar el archivo o estar incompleto; prueba otra vuelta."
    if "404" in message:
        return "No se ha encontrado la sesión o la vuelta seleccionada. Actualiza la lista."
    if "timed out" in message:
        return "El análisis ha tardado demasiado. Vuelve a intentarlo; la explicación con IA puede requerir más tiempo."
    if "503" in message or "connect" in message:
        return "No se puede acceder al servicio de análisis o a las sesiones guardadas. Comprueba que estén iniciados."
    if "400" in message or "422" in message:
        return "Los datos no permiten completar la comparación. Selecciona dos vueltas distintas con telemetría válida."
    return "No se ha podido completar la operación. Vuelve a intentarlo o comprueba el servicio de análisis."
