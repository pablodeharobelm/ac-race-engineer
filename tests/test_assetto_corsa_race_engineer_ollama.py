import json
from typing import Self
from urllib.error import URLError

import pytest

from ac_race_engineer.telemetry.assetto_corsa.race_engineer_llm_config import (
    RaceEngineerLLMSettings,
    load_race_engineer_llm_settings,
)
from ac_race_engineer.telemetry.assetto_corsa.race_engineer_llm_factory import (
    create_race_engineer_explanation_service,
)
from ac_race_engineer.telemetry.assetto_corsa.race_engineer_ollama import (
    OllamaRaceEngineerLLMClient,
)


class FakeHTTPResponse:
    def __init__(
        self,
        payload: dict,
    ) -> None:
        self.payload = payload

    def __enter__(
        self,
    ) -> Self:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        return None

    def read(
        self,
    ) -> bytes:
        return json.dumps(
            self.payload
        ).encode(
            "utf-8"
        )


def settings(
    *,
    provider: str = "ollama",
    model: str | None = "test-model",
) -> RaceEngineerLLMSettings:
    return RaceEngineerLLMSettings(
        provider=provider,
        model=model,
        base_url=(
            "http://127.0.0.1:11434"
        ),
        timeout_seconds=10.0,
    )


def test_ollama_client_generates_text(
    monkeypatch,
) -> None:
    captured = {}

    def fake_urlopen(
        request,
        timeout,
    ):
        captured[
            "url"
        ] = request.full_url

        captured[
            "timeout"
        ] = timeout

        captured[
            "payload"
        ] = json.loads(
            request.data.decode(
                "utf-8"
            )
        )

        return FakeHTTPResponse(
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        "Trabaja primero "
                        "la curva 1."
                    ),
                }
            }
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.telemetry."
            "assetto_corsa."
            "race_engineer_ollama.urlopen"
        ),
        fake_urlopen,
    )

    client = (
        OllamaRaceEngineerLLMClient(
            model="llama-test"
        )
    )

    result = client.generate(
        system_prompt="system",
        user_prompt="user",
    )

    assert (
        result
        == "Trabaja primero la curva 1."
    )

    assert (
        captured["url"]
        == (
            "http://127.0.0.1:11434"
            "/api/chat"
        )
    )

    assert (
        captured["timeout"]
        == 60.0
    )

    assert (
        captured["payload"][
            "model"
        ]
        == "llama-test"
    )

    assert (
        captured["payload"][
            "stream"
        ]
        is False
    )

    messages = (
        captured["payload"][
            "messages"
        ]
    )

    assert (
        messages[0]["role"]
        == "system"
    )

    assert (
        messages[1]["role"]
        == "user"
    )


def test_ollama_client_handles_connection_error(
    monkeypatch,
) -> None:
    def fake_urlopen(
        request,
        timeout,
    ):
        raise URLError(
            "connection refused"
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.telemetry."
            "assetto_corsa."
            "race_engineer_ollama.urlopen"
        ),
        fake_urlopen,
    )

    client = (
        OllamaRaceEngineerLLMClient(
            model="test-model"
        )
    )

    with pytest.raises(
        RuntimeError,
        match="connect to Ollama",
    ):
        client.generate(
            system_prompt="system",
            user_prompt="user",
        )


def test_ollama_client_rejects_invalid_response(
    monkeypatch,
) -> None:
    class InvalidResponse:
        def __enter__(
            self,
        ):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return None

        def read(
            self,
        ):
            return b"not-json"

    monkeypatch.setattr(
        (
            "ac_race_engineer.telemetry."
            "assetto_corsa."
            "race_engineer_ollama.urlopen"
        ),
        lambda request, timeout: (
            InvalidResponse()
        ),
    )

    client = (
        OllamaRaceEngineerLLMClient(
            model="test-model"
        )
    )

    with pytest.raises(
        RuntimeError,
        match="invalid JSON",
    ):
        client.generate(
            system_prompt="system",
            user_prompt="user",
        )


def test_factory_returns_none_when_disabled() -> None:
    service = (
        create_race_engineer_explanation_service(
            settings(
                provider="disabled",
                model=None,
            )
        )
    )

    assert service is None


def test_factory_builds_ollama_service() -> None:
    service = (
        create_race_engineer_explanation_service(
            settings()
        )
    )

    assert service is not None

    assert isinstance(
        service.client,
        OllamaRaceEngineerLLMClient,
    )


def test_factory_requires_model() -> None:
    with pytest.raises(
        ValueError,
        match="RACE_ENGINEER_LLM_MODEL",
    ):
        create_race_engineer_explanation_service(
            settings(
                model=None
            )
        )


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        create_race_engineer_explanation_service(
            settings(
                provider="unknown"
            )
        )


def test_loads_settings_from_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "RACE_ENGINEER_LLM_PROVIDER",
        "ollama",
    )

    monkeypatch.setenv(
        "RACE_ENGINEER_LLM_MODEL",
        "llama-local",
    )

    monkeypatch.setenv(
        "RACE_ENGINEER_LLM_BASE_URL",
        "http://localhost:9999/",
    )

    monkeypatch.setenv(
        "RACE_ENGINEER_LLM_TIMEOUT_SECONDS",
        "15",
    )

    loaded = (
        load_race_engineer_llm_settings()
    )

    assert (
        loaded.provider
        == "ollama"
    )

    assert (
        loaded.model
        == "llama-local"
    )

    assert (
        loaded.base_url
        == "http://localhost:9999"
    )

    assert (
        loaded.timeout_seconds
        == 15.0
    )


def test_rejects_invalid_timeout(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "RACE_ENGINEER_LLM_TIMEOUT_SECONDS",
        "invalid",
    )

    with pytest.raises(
        ValueError,
        match="must be numeric",
    ):
        load_race_engineer_llm_settings()


def test_rejects_empty_model_name() -> None:
    with pytest.raises(
        ValueError,
        match="model",
    ):
        OllamaRaceEngineerLLMClient(
            model="   "
        )