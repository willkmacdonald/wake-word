from __future__ import annotations

import numpy as np

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class PorcupineEngine:
    name = "porcupine"

    def __init__(self, porcupine: object, keyword_names: list[str], phrase_track: str) -> None:
        self.porcupine = porcupine
        self.keyword_names = keyword_names
        self.phrase_track = phrase_track
        self.sample_rate_hz = int(porcupine.sample_rate)
        self.frame_length = int(porcupine.frame_length)
        self._frames_seen = 0

    @classmethod
    def from_keywords(
        cls,
        access_key: str,
        keywords: list[str],
        phrase_track: str = "builtin-baseline",
    ) -> PorcupineEngine:
        import pvporcupine

        porcupine = pvporcupine.create(access_key=access_key, keywords=keywords)
        return cls(porcupine=porcupine, keyword_names=keywords, phrase_track=phrase_track)

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        pcm = np.frombuffer(frame.pcm, dtype=np.int16)
        if frame.sample_rate_hz != self.sample_rate_hz:
            raise ValueError(
                f"Porcupine requires {self.sample_rate_hz} Hz audio; got {frame.sample_rate_hz} Hz"
            )
        if frame.channels != 1:
            raise ValueError(f"Porcupine requires mono audio; got {frame.channels} channels")
        if pcm.shape != (self.frame_length,):
            raise ValueError(
                f"Porcupine requires {self.frame_length} samples per frame; got {pcm.size} "
                "samples. Configure the endpoint frame duration to match the Porcupine frame "
                "length or add a reframing buffer before this adapter."
            )

        self._frames_seen += 1
        keyword_index = int(self.porcupine.process(pcm))
        if keyword_index < 0:
            return None
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )
