from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path

import typer
from rich import print

from wake_word_endpoint.audio import GeneratedAudioSource, MicrophoneAudioSource
from wake_word_endpoint.config import load_config
from wake_word_endpoint.controller import EndpointController
from wake_word_endpoint.gateway_client import GatewayClient
from wake_word_endpoint.wake_engines.base import WakeDetection
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine

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


def _frame_count(seconds: int | float, frame_duration_ms: int) -> int:
    return max(1, math.ceil(float(seconds) * 1000 / frame_duration_ms))


def _gateway_token(token_env: str) -> str:
    token = os.environ.get(token_env)
    if not token:
        raise RuntimeError(f"{token_env} is not set")
    return token


def _print_detection(detection: WakeDetection) -> None:
    print(
        {
            "type": "wake.detected",
            "engine": detection.engine,
            "phrase_track": detection.phrase_track,
            "frame_index": detection.frame_index,
            "confidence": detection.confidence,
        }
    )


def build_wake_engine(
    engine: str,
    phrase_track: str,
    *,
    openwakeword_model: str = "hey_jarvis",
    openwakeword_threshold: float = 0.5,
    porcupine_keyword: str = "picovoice",
    porcupine_access_key_env: str = "PORCUPINE_ACCESS_KEY",
    microsoft_keyword_table: str | None = None,
    microsoft_sample_rate_hz: int = 16000,
    microsoft_channels: int = 1,
    sherpa_model_dir: str | None = None,
    sherpa_keywords_file: str | None = None,
    sherpa_num_threads: int = 2,
    sherpa_provider: str = "cpu",
):
    """Build the configured wake engine without importing optional SDKs unless needed."""
    normalized = engine.strip().lower()
    if normalized == "fake":
        return FakeWakeEngine(trigger_after_frames=10)
    if normalized == "openwakeword":
        from wake_word_endpoint.wake_engines.openwakeword import OpenWakeWordEngine

        return OpenWakeWordEngine.from_default_model(
            model_name=openwakeword_model,
            phrase_track=phrase_track,
            threshold=openwakeword_threshold,
        )
    if normalized == "porcupine":
        from wake_word_endpoint.wake_engines.porcupine import PorcupineEngine

        access_key = _gateway_token(porcupine_access_key_env)
        return PorcupineEngine.from_keywords(
            access_key=access_key,
            keywords=[porcupine_keyword],
            phrase_track=phrase_track,
        )
    if normalized == "microsoft-custom-keyword":
        from wake_word_endpoint.wake_engines.microsoft_custom_keyword import (
            MicrosoftCustomKeywordEngine,
        )

        if not microsoft_keyword_table:
            raise ValueError(
                "--microsoft-keyword-table is required when "
                "wake_word.engine is microsoft-custom-keyword"
            )
        return MicrosoftCustomKeywordEngine.from_table_file(
            table_file=microsoft_keyword_table,
            phrase_track=phrase_track,
            sample_rate_hz=microsoft_sample_rate_hz,
            channels=microsoft_channels,
        )
    if normalized == "sherpa-onnx":
        from wake_word_endpoint.wake_engines.sherpa_onnx import SherpaOnnxKeywordEngine

        if not sherpa_model_dir:
            raise ValueError("--sherpa-model-dir is required when wake_word.engine is sherpa-onnx")
        if not sherpa_keywords_file:
            raise ValueError(
                "--sherpa-keywords-file is required when wake_word.engine is sherpa-onnx"
            )
        return SherpaOnnxKeywordEngine.from_model_dir(
            model_dir=sherpa_model_dir,
            keywords_file=sherpa_keywords_file,
            phrase_track=phrase_track,
            num_threads=sherpa_num_threads,
            provider=sherpa_provider,
        )
    raise ValueError(f"unsupported wake-word engine: {engine}")


@app.command()
def run(
    config: Path,
    run_id: str = "manual-run",
    max_listen_seconds: int | None = None,
    openwakeword_model: str = "hey_jarvis",
    openwakeword_threshold: float = 0.5,
    porcupine_keyword: str = "picovoice",
    porcupine_access_key_env: str = "PORCUPINE_ACCESS_KEY",
    microsoft_keyword_table: str | None = None,
    sherpa_model_dir: str | None = None,
    sherpa_keywords_file: str | None = None,
    sherpa_num_threads: int = 2,
    sherpa_provider: str = "cpu",
) -> None:
    """Run the microphone endpoint with the wake engine selected in config."""
    loaded = load_config(config)
    token = _gateway_token(loaded.gateway.token_env)
    source = MicrophoneAudioSource(
        device=loaded.microphone.device,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )
    wake_engine = build_wake_engine(
        loaded.wake_word.engine,
        loaded.wake_word.phrase_track,
        openwakeword_model=openwakeword_model,
        openwakeword_threshold=openwakeword_threshold,
        porcupine_keyword=porcupine_keyword,
        porcupine_access_key_env=porcupine_access_key_env,
        microsoft_keyword_table=microsoft_keyword_table,
        microsoft_sample_rate_hz=loaded.microphone.sample_rate_hz,
        microsoft_channels=loaded.microphone.channels,
        sherpa_model_dir=sherpa_model_dir,
        sherpa_keywords_file=sherpa_keywords_file,
        sherpa_num_threads=sherpa_num_threads,
        sherpa_provider=sherpa_provider,
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
        wake_engine=wake_engine,
        gateway_client=gateway,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
        max_stream_frames=_frame_count(
            loaded.session.max_seconds,
            loaded.session.frame_duration_ms,
        ),
        on_detection=_print_detection,
    )
    max_listen_frames = (
        None
        if max_listen_seconds is None
        else _frame_count(max_listen_seconds, loaded.session.frame_duration_ms)
    )
    events = asyncio.run(controller.run_once(max_listen_frames=max_listen_frames))
    for event in events or []:
        print(event)


@app.command()
def run_fake(config: Path, token: str = "dev-token", run_id: str = "manual-run") -> None:
    """Run the endpoint with generated audio and a fake wake event."""
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
