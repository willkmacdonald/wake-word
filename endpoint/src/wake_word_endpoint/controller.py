from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import AsyncIterator, Iterator
from typing import Any

from wake_word_endpoint.audio import AudioFrame, AudioSource
from wake_word_endpoint.protocol import AudioSpec, SessionHello, WakeSpec
from wake_word_endpoint.wake_engines.base import WakeEngine


async def _async_frames(
    source_iter: Iterator[AudioFrame],
    max_frames: int,
) -> AsyncIterator[AudioFrame]:
    for _, frame in zip(range(max_frames), source_iter, strict=False):
        yield frame
        await asyncio.sleep(0)


class EndpointController:
    def __init__(
        self,
        endpoint_id: str,
        endpoint_type: str,
        run_id: str,
        audio_source: AudioSource,
        wake_engine: WakeEngine,
        gateway_client: Any,
        sample_rate_hz: int,
        channels: int,
        frame_duration_ms: int,
        max_stream_frames: int,
    ) -> None:
        self.endpoint_id = endpoint_id
        self.endpoint_type = endpoint_type
        self.run_id = run_id
        self.audio_source = audio_source
        self.wake_engine = wake_engine
        self.gateway_client = gateway_client
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms
        self.max_stream_frames = max_stream_frames

    async def run_once(self, max_listen_frames: int | None = None) -> list[Any]:
        source_iter = self.audio_source.frames(max_frames=max_listen_frames)
        for frame in source_iter:
            detection = self.wake_engine.process(frame)
            if detection is None:
                continue

            hello = SessionHello(
                endpoint_id=self.endpoint_id,
                endpoint_type=self.endpoint_type,
                run_id=self.run_id,
                audio=AudioSpec(
                    sample_rate_hz=self.sample_rate_hz,
                    channels=self.channels,
                    frame_duration_ms=self.frame_duration_ms,
                ),
                wake=WakeSpec(engine=detection.engine, phrase_track=detection.phrase_track),
                started_at=dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
            )
            return await self.gateway_client.stream_session(
                hello,
                _async_frames(source_iter, self.max_stream_frames),
            )
        return []
