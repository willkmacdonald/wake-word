from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class AudioFrame:
    pcm: bytes
    sample_rate_hz: int
    channels: int
    duration_ms: int

    @classmethod
    def pcm_silence(cls, sample_rate_hz: int, channels: int, duration_ms: int) -> AudioFrame:
        samples = int(sample_rate_hz * duration_ms / 1000) * channels
        return cls(
            pcm=np.zeros(samples, dtype=np.int16).tobytes(),
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            duration_ms=duration_ms,
        )


class AudioSource(Protocol):
    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        """Yield PCM audio frames."""


class GeneratedAudioSource:
    def __init__(self, sample_rate_hz: int, channels: int, frame_duration_ms: int) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms

    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        emitted = 0
        while max_frames is None or emitted < max_frames:
            emitted += 1
            yield AudioFrame.pcm_silence(
                sample_rate_hz=self.sample_rate_hz,
                channels=self.channels,
                duration_ms=self.frame_duration_ms,
            )


class MicrophoneAudioSource:
    def __init__(
        self,
        device: str | int | None,
        sample_rate_hz: int,
        channels: int,
        frame_duration_ms: int,
        overflow_policy: str = "skip",
    ) -> None:
        if overflow_policy not in {"skip", "raise"}:
            raise ValueError("overflow_policy must be 'skip' or 'raise'")
        self.device = device
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms
        self.overflow_policy = overflow_policy
        self.overflow_count = 0

    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        import sounddevice as sd

        frame_samples = int(self.sample_rate_hz * self.frame_duration_ms / 1000)
        emitted = 0
        with sd.RawInputStream(
            samplerate=self.sample_rate_hz,
            blocksize=frame_samples,
            device=self.device,
            channels=self.channels,
            dtype="int16",
        ) as stream:
            while max_frames is None or emitted < max_frames:
                data, overflowed = stream.read(frame_samples)
                if overflowed:
                    self.overflow_count += 1
                    if self.overflow_policy == "raise":
                        raise RuntimeError("microphone input overflowed")
                    continue
                emitted += 1
                yield AudioFrame(
                    pcm=bytes(data),
                    sample_rate_hz=self.sample_rate_hz,
                    channels=self.channels,
                    duration_ms=self.frame_duration_ms,
                )
