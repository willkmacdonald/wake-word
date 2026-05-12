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


@app.command()
def audio_profile(config: Path, frames: int = 200) -> None:
    """Capture microphone frames and print simple timing/buffer profile data."""
    import statistics
    import time

    from wake_word_endpoint.audio import MicrophoneAudioSource

    loaded = load_config(config)
    source = MicrophoneAudioSource(
        device=loaded.microphone.device,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )

    timestamps: list[float] = []
    byte_counts: list[int] = []
    for frame in source.frames(max_frames=frames):
        timestamps.append(time.monotonic())
        byte_counts.append(len(frame.pcm))

    intervals_ms = [
        (current - previous) * 1000
        for previous, current in zip(timestamps, timestamps[1:], strict=False)
    ]
    print(
        {
            "frames": len(byte_counts),
            "expected_frame_duration_ms": loaded.session.frame_duration_ms,
            "bytes_per_frame_min": min(byte_counts) if byte_counts else None,
            "bytes_per_frame_max": max(byte_counts) if byte_counts else None,
            "interval_ms_mean": round(statistics.mean(intervals_ms), 2) if intervals_ms else None,
            "interval_ms_max": round(max(intervals_ms), 2) if intervals_ms else None,
        }
    )


@app.command()
def run_fake(config: Path, token: str = "dev-token", run_id: str = "manual-run") -> None:
    """Run the endpoint with generated audio and a fake wake event."""
    import asyncio

    from wake_word_endpoint.audio import GeneratedAudioSource
    from wake_word_endpoint.controller import EndpointController
    from wake_word_endpoint.gateway_client import GatewayClient
    from wake_word_endpoint.wake_engines.fake import FakeWakeEngine

    loaded = load_config(config)
    source = GeneratedAudioSource(
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )
    gateway = GatewayClient(
        url=loaded.gateway.url,
        endpoint_id=loaded.endpoint.id,
        token=token,
    )
    controller = EndpointController(
        endpoint_id=loaded.endpoint.id,
        endpoint_type=loaded.endpoint.type,
        run_id=run_id,
        audio_source=source,
        wake_engine=FakeWakeEngine(trigger_after_frames=10),
        gateway_client=gateway,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
        max_stream_frames=100,
    )
    events = asyncio.run(controller.run_once(max_listen_frames=200))
    for event in events or []:
        print(event)
