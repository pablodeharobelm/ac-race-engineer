from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from ac_race_engineer.dashboard.locale_es import format_date, friendly_name

ASSETS = Path(__file__).parent / "assets"


@dataclass(frozen=True)
class SessionImage:
    path: Path
    provisional: bool


def session_image(kind: str, key: str | None, game_directory: str = "") -> SessionImage:
    fallback = SessionImage(ASSETS / ("car.svg" if kind == "car" else "track.svg"), True)
    if not game_directory or not key or any(character in key for character in ("/", "\\", ":", "..")):
        return fallback
    folder = Path(game_directory) / "content" / ("cars" if kind == "car" else "tracks") / key
    try:
        if kind == "car":
            candidates = [folder / "ui" / "preview.png", folder / "ui" / "preview.jpg"]
            candidates.extend(sorted((folder / "skins").glob("*/preview.jpg")))
        else:
            candidates = [folder / "map.png", folder / "ui" / "preview.png"]
        for candidate in candidates:
            if candidate.is_file():
                return SessionImage(candidate, False)
    except OSError:
        pass
    return fallback


def render_session_identity(session: dict) -> None:
    game_directory = st.session_state.get("assetto_corsa_path", "")
    car_column, track_column = st.columns(2)
    with car_column, st.container(border=True):
        image = session_image("car", session["car_key"], game_directory)
        st.image(str(image.path), width="stretch")
        st.subheader(friendly_name(session["car_key"]))
        st.caption("Ilustración provisional del coche" if image.provisional else "Imagen del coche incluida en el juego")
    with track_column, st.container(border=True):
        image = session_image("track", session.get("track_key"), game_directory)
        st.image(str(image.path), width="stretch")
        st.subheader(friendly_name(session.get("track_key")))
        st.caption("Esquema ilustrativo; no es el trazado real" if image.provisional else "Imagen del circuito incluida en el juego")
    st.caption(
        f"{format_date(session.get('started_at') or session.get('created_at'))} · "
        f"{session['lap_count']} vueltas registradas"
    )
