from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.gateway_client import GatewayClient, GatewayHeaders
from wake_word_endpoint.protocol import AudioSpec, SessionHello, WakeSpec


def test_gateway_headers_include_endpoint_id_and_bearer_token():
    headers = GatewayHeaders(endpoint_id="mac-studio-01", token="dev-token").to_headers()

    assert headers["Authorization"] == "Bearer dev-token"
    assert headers["X-Endpoint-Id"] == "mac-studio-01"


class FakeWebSocket:
    def __init__(self, incoming: list[str]) -> None:
        self.incoming = incoming
        self.sent: list[str | bytes] = []
        self.recv_count = 0

    async def send(self, data: str | bytes) -> None:
        self.sent.append(data)

    async def recv(self) -> str:
        if self.recv_count == 0:
            assert len(self.sent) == 1
            assert isinstance(self.sent[0], str)
            assert json.loads(self.sent[0])["type"] == "hello"
        self.recv_count += 1
        return self.incoming.pop(0)


class FakeConnect:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket

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
