from ac_race_engineer.telemetry.assetto_corsa.race_engineer_llm_config import (
    RaceEngineerLLMSettings,
    load_race_engineer_llm_settings,
)
from ac_race_engineer.telemetry.assetto_corsa.race_engineer_ollama import (
    OllamaRaceEngineerLLMClient,
)
from ac_race_engineer.telemetry.assetto_corsa.trace_race_engineer_llm import (
    AssettoCorsaRaceEngineerExplanationService,
)


def create_race_engineer_explanation_service(
    settings: (
        RaceEngineerLLMSettings
        | None
    ) = None,
) -> (
    AssettoCorsaRaceEngineerExplanationService
    | None
):
    resolved = (
        settings
        or load_race_engineer_llm_settings()
    )

    if resolved.provider in {
        "",
        "disabled",
        "none",
        "off",
    }:
        return None

    if resolved.provider == "ollama":
        if resolved.model is None:
            raise ValueError(
                "RACE_ENGINEER_LLM_MODEL "
                "is required when using Ollama"
            )

        client = (
            OllamaRaceEngineerLLMClient(
                model=resolved.model,
                base_url=resolved.base_url,
                timeout_seconds=(
                    resolved.timeout_seconds
                ),
            )
        )

        return (
            AssettoCorsaRaceEngineerExplanationService(
                client=client
            )
        )

    raise ValueError(
        "Unsupported Race Engineer "
        f"LLM provider: {resolved.provider}"
    )