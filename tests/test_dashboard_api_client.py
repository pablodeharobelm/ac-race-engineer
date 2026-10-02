import json
from typing import Any

import pytest

from ac_race_engineer.dashboard.api_client import (
    RaceEngineerAPIClient,
    RaceEngineerAPIError,
)


class FakeHTTPResponse:
    def __init__(
        self,
        payload: Any,
    ) -> None:
        self._payload = payload

    def __enter__(
        self,
    ):
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
            self._payload
        ).encode(
            "utf-8"
        )


def test_health_request(
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
            "method"
        ] = request.method

        captured[
            "timeout"
        ] = timeout

        return FakeHTTPResponse(
            {
                "status": "ok",
            }
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.dashboard."
            "api_client.urlopen"
        ),
        fake_urlopen,
    )

    client = RaceEngineerAPIClient(
        base_url="http://localhost:8000/",
        timeout_seconds=12.0,
    )

    response = client.health()

    assert response == {
        "status": "ok",
    }

    assert (
        captured["url"]
        == "http://localhost:8000/health"
    )

    assert (
        captured["method"]
        == "GET"
    )

    assert (
        captured["timeout"]
        == 12.0
    )


def test_analyze_posts_json(
    monkeypatch,
) -> None:
    captured = {}

    def fake_urlopen(
        request,
        timeout,
    ):
        captured[
            "method"
        ] = request.method

        captured[
            "payload"
        ] = json.loads(
            request.data.decode(
                "utf-8"
            )
        )

        return FakeHTTPResponse(
            {
                "trend": "neutral",
            }
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.dashboard."
            "api_client.urlopen"
        ),
        fake_urlopen,
    )

    client = RaceEngineerAPIClient()

    payload = {
        "reference_lap_number": 1,
        "target_lap_number": 2,
    }

    response = client.analyze(
        payload
    )

    assert (
        captured["method"]
        == "POST"
    )

    assert (
        captured["payload"]
        == payload
    )

    assert response[
        "trend"
    ] == "neutral"


def test_list_recent(
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

        return FakeHTTPResponse(
            [
                {
                    "analysis_id": "a-1",
                }
            ]
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.dashboard."
            "api_client.urlopen"
        ),
        fake_urlopen,
    )

    client = RaceEngineerAPIClient()

    response = client.list_recent(
        limit=5
    )

    assert len(
        response
    ) == 1

    assert (
        response[0][
            "analysis_id"
        ]
        == "a-1"
    )

    assert (
        captured["url"]
        == (
            "http://127.0.0.1:8000/"
            "v1/race-engineer/"
            "analyses/recent?limit=5"
        )
    )


def test_get_analysis_encodes_id(
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

        return FakeHTTPResponse(
            {
                "analysis_id": "analysis / 1",
            }
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.dashboard."
            "api_client.urlopen"
        ),
        fake_urlopen,
    )

    client = RaceEngineerAPIClient()

    response = client.get_analysis(
        "analysis / 1"
    )

    assert (
        response["analysis_id"]
        == "analysis / 1"
    )

    assert (
        captured["url"]
        == (
            "http://127.0.0.1:8000/"
            "v1/race-engineer/"
            "analyses/analysis%20%2F%201"
        )
    )


def test_list_for_session_encodes_id(
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

        return FakeHTTPResponse(
            []
        )

    monkeypatch.setattr(
        (
            "ac_race_engineer.dashboard."
            "api_client.urlopen"
        ),
        fake_urlopen,
    )

    client = RaceEngineerAPIClient()

    response = client.list_for_session(
        "race night"
    )

    assert response == []

    assert (
        captured["url"]
        == (
            "http://127.0.0.1:8000/"
            "v1/race-engineer/"
            "analyses/session/race%20night"
        )
    )


def test_rejects_invalid_limit() -> None:
    client = RaceEngineerAPIClient()

    with pytest.raises(
        ValueError,
        match="limit",
    ):
        client.list_recent(
            limit=0
        )


def test_rejects_blank_analysis_id() -> None:
    client = RaceEngineerAPIClient()

    with pytest.raises(
        ValueError,
        match="analysis_id",
    ):
        client.get_analysis(
            "   "
        )


def test_rejects_blank_session_id() -> None:
    client = RaceEngineerAPIClient()

    with pytest.raises(
        ValueError,
        match="session_id",
    ):
        client.list_for_session(
            "   "
        )


def test_rejects_empty_base_url() -> None:
    with pytest.raises(
        ValueError,
        match="base_url",
    ):
        RaceEngineerAPIClient(
            base_url="   "
        )


def test_rejects_invalid_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="timeout_seconds",
    ):
        RaceEngineerAPIClient(
            timeout_seconds=0.0
        )


def test_invalid_json_response_raises(
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
        ) -> None:
            return None

        def read(
            self,
        ) -> bytes:
            return b"invalid-json"

    monkeypatch.setattr(
        (
            "ac_race_engineer.dashboard."
            "api_client.urlopen"
        ),
        lambda request, timeout: (
            InvalidResponse()
        ),
    )

    client = RaceEngineerAPIClient()

    with pytest.raises(
        RaceEngineerAPIError,
        match="invalid JSON",
    ):
        client.health()