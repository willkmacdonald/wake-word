from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

PROTOCOL_VERSION = "wake-word.v1"


@dataclass(frozen=True)
class AudioSpec:
    sample_rate_hz: int
    channels: int
    frame_duration_ms: int
    format: str = "pcm_s16le"

    def to_wire(self) -> dict[str, int | str]:
        return {
            "format": self.format,
            "sampleRateHz": self.sample_rate_hz,
            "channels": self.channels,
            "frameDurationMs": self.frame_duration_ms,
        }


@dataclass(frozen=True)
class WakeSpec:
    engine: str
    phrase_track: str

    def to_wire(self) -> dict[str, str]:
        return {"engine": self.engine, "phraseTrack": self.phrase_track}


@dataclass(frozen=True)
class SessionHello:
    endpoint_id: str
    endpoint_type: str
    run_id: str
    audio: AudioSpec
    wake: WakeSpec
    started_at: str
    type: Literal["hello"] = "hello"
    protocol_version: str = PROTOCOL_VERSION

    def to_wire(self) -> dict[str, object]:
        return {
            "type": self.type,
            "protocolVersion": self.protocol_version,
            "endpointId": self.endpoint_id,
            "endpointType": self.endpoint_type,
            "runId": self.run_id,
            "audio": self.audio.to_wire(),
            "wake": self.wake.to_wire(),
            "startedAt": self.started_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_wire(), separators=(",", ":"))


@dataclass(frozen=True)
class ClientStop:
    reason: str
    type: Literal["stop"] = "stop"

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass(frozen=True)
class ServerMessage:
    type: str
    session_id: str | None = None
    text: str | None = None
    offset_ms: int | None = None
    reason: str | None = None
    message: str | None = None


def parse_server_message(raw: str) -> ServerMessage:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server message must be a JSON object")

    return ServerMessage(
        type=str(payload["type"]),
        session_id=payload.get("sessionId"),
        text=payload.get("text"),
        offset_ms=payload.get("offsetMs"),
        reason=payload.get("reason"),
        message=payload.get("message"),
    )
