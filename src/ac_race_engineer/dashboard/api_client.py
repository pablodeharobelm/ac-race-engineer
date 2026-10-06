import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class RaceEngineerAPIError(RuntimeError):
    """Raised when the Race Engineer API request fails."""


@dataclass(frozen=True)
class RaceEngineerAPIClient:
    base_url: str = "http://127.0.0.1:8000"
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        normalized_url = self.base_url.strip().rstrip("/")

        if not normalized_url:
            raise ValueError(
                "base_url cannot be empty"
            )

        if self.timeout_seconds <= 0.0:
            raise ValueError(
                "timeout_seconds must be greater than 0"
            )

        object.__setattr__(
            self,
            "base_url",
            normalized_url,
        )

    def health(
        self,
    ) -> dict[str, Any]:
        return self._request(
            method="GET",
            path="/health",
        )

    def analyze(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/race-engineer/analyze",
            payload=payload,
        )

    def list_sessions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        response = self._request(method="GET", path=f"/v1/sessions?{urlencode({'limit': limit})}")
        if not isinstance(response, list):
            raise RaceEngineerAPIError("API returned an invalid session list")
        return response

    @staticmethod
    def _session_path(session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise ValueError("session_id cannot be empty")
        return f"/v1/sessions/{quote(normalized, safe='')}"

    def list_laps(self, session_id: str) -> list[dict[str, Any]]:
        response = self._request(method="GET", path=f"{self._session_path(session_id)}/laps")
        if not isinstance(response, list):
            raise RaceEngineerAPIError("API returned an invalid lap list")
        return response

    def get_trace(self, session_id: str, lap_number: int) -> dict[str, Any]:
        if lap_number <= 0:
            raise ValueError("lap_number must be greater than 0")
        response = self._request(
            method="GET", path=f"{self._session_path(session_id)}/laps/{lap_number}/trace",
        )
        if not isinstance(response, dict) or not isinstance(response.get("samples"), list):
            raise RaceEngineerAPIError("API returned an invalid driving trace")
        return response

    def analyze_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            method="POST", path=f"{self._session_path(session_id)}/analyze", payload=payload,
        )

    def get_analysis(
        self,
        analysis_id: str,
    ) -> dict[str, Any]:
        normalized_analysis_id = analysis_id.strip()

        if not normalized_analysis_id:
            raise ValueError(
                "analysis_id cannot be empty"
            )

        return self._request(
            method="GET",
            path=(
                "/v1/race-engineer/analyses/"
                f"{quote(normalized_analysis_id, safe='')}"
            ),
        )

    def list_recent(
        self,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError(
                "limit must be greater than 0"
            )

        query = urlencode(
            {
                "limit": limit,
            }
        )

        response = self._request(
            method="GET",
            path=(
                "/v1/race-engineer/"
                f"analyses/recent?{query}"
            ),
        )

        if not isinstance(
            response,
            list,
        ):
            raise RaceEngineerAPIError(
                "API returned an invalid history response"
            )

        return response

    def list_for_session(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        normalized_session_id = session_id.strip()

        if not normalized_session_id:
            raise ValueError(
                "session_id cannot be empty"
            )

        response = self._request(
            method="GET",
            path=(
                "/v1/race-engineer/"
                "analyses/session/"
                f"{quote(normalized_session_id, safe='')}"
            ),
        )

        if not isinstance(
            response,
            list,
        ):
            raise RaceEngineerAPIError(
                "API returned an invalid session history response"
            )

        return response

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = None

        headers = {
            "Accept": "application/json",
        }

        if payload is not None:
            data = json.dumps(
                payload
            ).encode(
                "utf-8"
            )

            headers[
                "Content-Type"
            ] = "application/json"

        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read()

        except HTTPError as exc:
            detail = self._read_http_error(
                exc
            )

            raise RaceEngineerAPIError(
                f"API returned HTTP {exc.code}: {detail}"
            ) from exc

        except URLError as exc:
            raise RaceEngineerAPIError(
                "Could not connect to the Race Engineer API"
            ) from exc

        except TimeoutError as exc:
            raise RaceEngineerAPIError(
                "Race Engineer API request timed out. "
                "The local LLM may still be generating "
                "the explanation."
            ) from exc

        try:
            return json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise RaceEngineerAPIError(
                "API returned an invalid JSON response"
            ) from exc

    @staticmethod
    def _read_http_error(
        exc: HTTPError,
    ) -> str:
        try:
            raw = exc.read()

            payload = json.loads(
                raw.decode(
                    "utf-8"
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return str(
                exc.reason
            )

        if isinstance(
            payload,
            dict,
        ):
            detail = payload.get(
                "detail"
            )

            if isinstance(
                detail,
                str,
            ):
                return detail

        return str(
            exc.reason
        )
