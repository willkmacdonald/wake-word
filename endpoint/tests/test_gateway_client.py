from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.gateway_client import (
    GatewayClient,
    GatewayConnectionError,
    GatewayHeaders,
    GatewayRetryPolicy,
)
from wake_word_endpoint.protocol import AudioSpec, SessionHello, WakeSpec, parse_server_message


def test_gateway_headers_include_endpoint_id_and_bearer_token():
    headers = GatewayHeaders(endpoint_id="mac-studio-01", token="dev-token").to_headers()

    assert headers["Authorization"] == "Bearer dev-token"
    assert headers["X-Endpoint-Id"] == "mac-studio-01"


def test_retry_policy_uses_bounded_exponential_backoff_without_jitter_for_tests():
    policy = GatewayRetryPolicy(
        max_attempts=4,
        base_delay_seconds=0.25,
        max_delay_seconds=1.0,
        jitter_ratio=0.0,
    )

    assert [policy.delay_for_attempt(attempt) for attempt in range(3)] == [0.25, 0.5, 1.0]


def test_retry_policy_rejects_invalid_attempt_count():
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        GatewayRetryPolicy(max_attempts=0)


def test_gateway_connection_error_names_endpoint_and_attempts():
    error = GatewayConnectionError(endpoint_id="mac-studio-01", attempts=3, reason="refused")

    assert "mac-studio-01" in str(error)
    assert "3 attempts" in str(error)
    assert "refused" in str(error)


class FakeWebSocket:
    def __init__(self, incoming: list[str]) -> None:
        self.incoming = incoming
        self.sent: list[str | bytes] = []
        self.recv_count = 0
        self.close_count = 0

    async def send(self, data: str | bytes) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if self.recv_count == 0:
            assert len(self.sent) == 1
            assert isinstance(self.sent[0], str)
            assert json.loads(self.sent[0])["type"] == "hello"
        self.recv_count += 1
        return self.incoming.pop(0)

    async def close(self) -> None:
        self.close_count += 1


class FakeConnect:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket

    def __await__(self):
        async def connect() -> FakeWebSocket:
            return self.websocket

        return connect().__await__()

    async def __aenter__(self) -> FakeWebSocket:
        return self.websocket

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def gateway_event(payload: dict[str, object]) -> str:
    return json.dumps(payload)


def accepted_event() -> str:
    return gateway_event(
        {
            "type": "session.accepted",
            "sessionId": "session-001",
            "maxSessionSeconds": 60,
            "acceptedAudio": {
                "format": "pcm_s16le",
                "sampleRateHz": 16000,
                "channels": 1,
            },
        }
    )


def test_parse_session_lifecycle_events():
    accepted = parse_server_message(
        """
        {
          "type": "session.accepted",
          "sessionId": "abc",
          "maxSessionSeconds": 60,
          "acceptedAudio": {
            "format": "pcm_s16le",
            "sampleRateHz": 16000,
            "channels": 1
          }
        }
        """
    )
    ended = parse_server_message('{"type":"session.ended","sessionId":"abc","reason":"manual"}')

    assert accepted.type == "session.accepted"
    assert accepted.session_id == "abc"
    assert ended.type == "session.ended"
    assert ended.reason == "manual"


def hello() -> SessionHello:
    return SessionHello(
        endpoint_id="mac-studio-01",
        endpoint_type="mac-studio",
        run_id="run-001",
        audio=AudioSpec(sample_rate_hz=16000, channels=1, frame_duration_ms=20),
        wake=WakeSpec(engine="fake", phrase_track="builtin-baseline"),
        started_at="2026-05-11T18:00:00Z",
    )


async def audio_frames() -> AsyncIterator[AudioFrame]:
    yield AudioFrame(pcm=b"frame-1", sample_rate_hz=16000, channels=1, duration_ms=20)
    yield AudioFrame(pcm=b"frame-2", sample_rate_hz=16000, channels=1, duration_ms=20)


@pytest.mark.asyncio
async def test_stream_session_sends_hello_waits_for_accepted_streams_audio_and_returns_events(
    monkeypatch: pytest.MonkeyPatch,
):
    websocket = FakeWebSocket(
        [
            accepted_event(),
            gateway_event(
                {
                    "type": "transcript.partial",
                    "sessionId": "session-001",
                    "text": "wake",
                    "offsetMs": 120,
                }
            ),
            gateway_event(
                {
                    "type": "session.ended",
                    "sessionId": "session-001",
                    "reason": "client_stop",
                }
            ),
        ]
    )

    monkeypatch.setattr(
        "wake_word_endpoint.gateway_client.websockets.connect",
        lambda *args, **kwargs: FakeConnect(websocket),
    )

    events = await GatewayClient(
        url="wss://gateway.example.test/sessions",
        endpoint_id="mac-studio-01",
        token="dev-token",
    ).stream_session(hello(), audio_frames(), stop_reason="test_complete")

    assert [event.type for event in events] == [
        "session.accepted",
        "transcript.partial",
        "session.ended",
    ]
    assert websocket.sent[1:3] == [b"frame-1", b"frame-2"]
    assert json.loads(websocket.sent[3]) == {"reason": "test_complete", "type": "stop"}


@pytest.mark.asyncio
async def test_stream_session_retries_initial_connection_failure(monkeypatch: pytest.MonkeyPatch):
    websocket = FakeWebSocket(
        [
            accepted_event(),
            gateway_event(
                {
                    "type": "session.ended",
                    "sessionId": "session-001",
                    "reason": "client_stop",
                }
            ),
        ]
    )
    attempts = 0
    sleeps: list[float] = []

    async def connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("refused")
        return websocket

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("wake_word_endpoint.gateway_client.websockets.connect", connect)
    monkeypatch.setattr("wake_word_endpoint.gateway_client.asyncio.sleep", sleep)

    events = await GatewayClient(
        url="wss://gateway.example.test/sessions",
        endpoint_id="mac-studio-01",
        token="dev-token",
        retry_policy=GatewayRetryPolicy(max_attempts=2, jitter_ratio=0.0),
    ).stream_session(hello(), audio_frames(), stop_reason="test_complete")

    assert attempts == 2
    assert sleeps == [0.25]
    assert [event.type for event in events] == ["session.accepted", "session.ended"]


@pytest.mark.asyncio
async def test_stream_session_rejects_initial_non_accepted_event_before_streaming_audio(
    monkeypatch: pytest.MonkeyPatch,
):
    websocket = FakeWebSocket(
        [
            gateway_event({"type": "error", "message": "not authorized"}),
        ]
    )

    monkeypatch.setattr(
        "wake_word_endpoint.gateway_client.websockets.connect",
        lambda *args, **kwargs: FakeConnect(websocket),
    )

    with pytest.raises(RuntimeError, match="gateway first event must be session.accepted"):
        await GatewayClient(
            url="wss://gateway.example.test/sessions",
            endpoint_id="mac-studio-01",
            token="dev-token",
        ).stream_session(hello(), audio_frames())

    assert len(websocket.sent) == 1
