import json
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)


class OllamaRaceEngineerLLMClient:
    """
    Race Engineer LLM client backed by Ollama.

    The client is intentionally small and provider-specific.

    Domain logic remains inside the deterministic
    Race Engineer services.
    """

    def __init__(
        self,
        *,
        model: str,
        base_url: str = (
            "http://127.0.0.1:11434"
        ),
        timeout_seconds: float = 60.0,
    ) -> None:
        normalized_model = (
            model.strip()
        )

        normalized_url = (
            base_url.strip().rstrip("/")
        )

        if not normalized_model:
            raise ValueError(
                "model cannot be empty"
            )

        if not normalized_url:
            raise ValueError(
                "base_url cannot be empty"
            )

        if timeout_seconds <= 0.0:
            raise ValueError(
                "timeout_seconds must be "
                "greater than 0"
            )

        self.model = normalized_model
        self.base_url = normalized_url
        self.timeout_seconds = (
            timeout_seconds
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        system_prompt
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        user_prompt
                    ),
                },
            ],
            "options": {
                "temperature": 0.2,
            },
        }

        encoded = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        request = Request(
            (
                f"{self.base_url}"
                "/api/chat"
            ),
            data=encoded,
            headers={
                "Content-Type": (
                    "application/json"
                ),
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=(
                    self.timeout_seconds
                ),
            ) as response:
                raw = response.read()

        except HTTPError as exc:
            raise RuntimeError(
                "Ollama returned HTTP "
                f"{exc.code}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                "Could not connect to Ollama"
            ) from exc

        try:
            decoded = json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError(
                "Ollama returned an invalid "
                "JSON response"
            ) from exc

        message = decoded.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            raise TypeError(
                "Ollama response does not "
                "contain a valid message"
            )

        content = message.get(
            "content"
        )

        if not isinstance(
            content,
            str,
        ):
            raise TypeError(
                "Ollama response does not "
                "contain valid text"
            )

        return content