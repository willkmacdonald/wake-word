from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from wake_word_endpoint.config import load_config

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Wake-word endpoint command line tools."""


@app.command()
def config_check(config: Path) -> None:
    """Load an endpoint config and print the effective endpoint identity."""
    loaded = load_config(config)
    print(
        {
            "endpoint_id": loaded.endpoint.id,
            "endpoint_type": loaded.endpoint.type,
            "wake_engine": loaded.wake_word.engine,
            "gateway_url": loaded.gateway.url,
        }
    )


@app.command()
def mic_probe(config: Path, frames: int = 50) -> None:
    """Capture a short microphone sample and print frame statistics."""
    from wake_word_endpoint.audio import MicrophoneAudioSource

    loaded = load_config(config)
    source = MicrophoneAudioSource(
        device=loaded.microphone.device,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )
    captured = list(source.frames(max_frames=frames))
    total_bytes = sum(len(frame.pcm) for frame in captured)
    print(
        {
            "frames": len(captured),
            "total_bytes": total_bytes,
            "sample_rate_hz": loaded.microphone.sample_rate_hz,
            "channels": loaded.microphone.channels,
        }
    )
