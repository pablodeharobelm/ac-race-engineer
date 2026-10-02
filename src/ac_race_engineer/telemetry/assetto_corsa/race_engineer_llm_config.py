import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RaceEngineerLLMSettings:
    provider: str

    model: str | None

    base_url: str

    timeout_seconds: float


def load_race_engineer_llm_settings(
) -> RaceEngineerLLMSettings:
    provider = os.getenv(
        "RACE_ENGINEER_LLM_PROVIDER",
        "disabled",
    ).strip().lower()

    model = os.getenv(
        "RACE_ENGINEER_LLM_MODEL"
    )

    if model is not None:
        model = model.strip()

        if not model:
            model = None

    base_url = os.getenv(
        "RACE_ENGINEER_LLM_BASE_URL",
        "http://127.0.0.1:11434",
    ).strip()

    timeout_raw = os.getenv(
        "RACE_ENGINEER_LLM_TIMEOUT_SECONDS",
        "60",
    )

    try:
        timeout_seconds = float(
            timeout_raw
        )

    except ValueError as exc:
        raise ValueError(
            "RACE_ENGINEER_LLM_TIMEOUT_SECONDS "
            "must be numeric"
        ) from exc

    if timeout_seconds <= 0.0:
        raise ValueError(
            "RACE_ENGINEER_LLM_TIMEOUT_SECONDS "
            "must be greater than 0"
        )

    if not base_url:
        raise ValueError(
            "RACE_ENGINEER_LLM_BASE_URL "
            "cannot be empty"
        )

    return RaceEngineerLLMSettings(
        provider=provider,
        model=model,
        base_url=base_url.rstrip("/"),
        timeout_seconds=timeout_seconds,
    )