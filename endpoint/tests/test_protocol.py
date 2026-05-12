import json

import pytest
from wake_word_endpoint.protocol import AudioSpec, SessionHello, WakeSpec, parse_server_message


def test_session_hello_serializes_to_gateway_contract():
    hello = SessionHello(
        endpoint_id="mac-studio-01",
        endpoint_type="mac-studio",
        run_id="run-001",
        audio=AudioSpec(sample_rate_hz=16000, channels=1, frame_duration_ms=20),
        wake=WakeSpec(engine="fake", phrase_track="builtin-baseline"),
        started_at="2026-05-11T18:00:00Z",
    )

    payload = json.loads(hello.to_json())

    assert payload == {
        "type": "hello",
        "protocolVersion": "wake-word.v1",
        "endpointId": "mac-studio-01",
        "endpointType": "mac-studio",
        "runId": "run-001",
        "audio": {
            "format": "pcm_s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "frameDurationMs": 20,
        },
        "wake": {
            "engine": "fake",
            "phraseTrack": "builtin-baseline",
        },
        "startedAt": "2026-05-11T18:00:00Z",
    }


def test_parse_transcript_event_from_gateway():
    event = parse_server_message(
        json.dumps(
            {
                "type": "transcript.partial",
                "sessionId": "session-001",
                "text": "scalpel",
                "offsetMs": 320,
            }
        )
    )

    assert event.type == "transcript.partial"
    assert event.session_id == "session-001"
    assert event.text == "scalpel"
    assert event.offset_ms == 320


def test_parse_session_accepted_event_from_gateway():
    event = parse_server_message(
        json.dumps(
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
    )

    assert event.type == "session.accepted"
    assert event.session_id == "session-001"


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "transcript.partial", "sessionId": "session-001", "offsetMs": 320},
        {"type": "session.accepted", "maxSessionSeconds": 60},
        {"type": "error"},
        {"type": 42},
    ],
)
def test_parse_server_message_rejects_invalid_event_shapes(payload):
    with pytest.raises(ValueError):
        parse_server_message(json.dumps(payload))
