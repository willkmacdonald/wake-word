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
        self._frames_seen += 1
        pcm = np.frombuffer(frame.pcm, dtype=np.int16)
        keyword_index = int(self.porcupine.process(pcm))
        if keyword_index < 0:
            return None
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )
