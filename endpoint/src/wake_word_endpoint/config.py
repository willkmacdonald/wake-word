from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EndpointConfig:
    id: str
    type: str


@dataclass(frozen=True)
class MicrophoneConfig:
    device: str | None
    sample_rate_hz: int
    channels: int


@dataclass(frozen=True)
class WakeWordConfig:
    engine: str
    phrase_track: str


@dataclass(frozen=True)
class GatewayConfig:
    url: str
    token_env: str


@dataclass(frozen=True)
class SessionConfig:
    frame_duration_ms: int
    max_seconds: int


@dataclass(frozen=True)
class AppConfig:
    endpoint: EndpointConfig
    microphone: MicrophoneConfig
    wake_word: WakeWordConfig
    gateway: GatewayConfig
    session: SessionConfig


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"missing config section: {name}")
    return value


def load_config(path: str | Path) -> AppConfig:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("config file must contain a mapping")

    endpoint = _section(data, "endpoint")
    microphone = _section(data, "microphone")
    wake_word = _section(data, "wake_word")
    gateway = _section(data, "gateway")
    session = _section(data, "session")

    return AppConfig(
        endpoint=EndpointConfig(id=str(endpoint["id"]), type=str(endpoint["type"])),
        microphone=MicrophoneConfig(
            device=microphone.get("device"),
            sample_rate_hz=int(microphone["sample_rate_hz"]),
            channels=int(microphone["channels"]),
        ),
        wake_word=WakeWordConfig(
            engine=str(wake_word["engine"]),
            phrase_track=str(wake_word["phrase_track"]),
        ),
        gateway=GatewayConfig(url=str(gateway["url"]), token_env=str(gateway["token_env"])),
        session=SessionConfig(
            frame_duration_ms=int(session["frame_duration_ms"]),
            max_seconds=int(session["max_seconds"]),
        ),
    )
