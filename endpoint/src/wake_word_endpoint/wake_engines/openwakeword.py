from __future__ import annotations

import numpy as np

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class OpenWakeWordEngine:
    name = "openwakeword"

    def __init__(
        self,
        model: object,
        model_name: str,
        phrase_track: str,
        threshold: float = 0.5,
    ) -> None:
        self.model = model
        self.model_name = model_name
        self.phrase_track = phrase_track
        self.threshold = threshold
        self._frames_seen = 0

    @classmethod
    def from_default_model(
        cls,
        model_name: str = "hey_jarvis",
        phrase_track: str = "builtin-baseline",
        threshold: float = 0.5,
    ) -> OpenWakeWordEngine:
        from openwakeword.model import Model

        return cls(
            model=Model(wakeword_models=[model_name]),
            model_name=model_name,
            phrase_track=phrase_track,
            threshold=threshold,
        )

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        self._frames_seen += 1
        pcm = np.frombuffer(frame.pcm, dtype=np.int16)
        prediction = self.model.predict(pcm)
        confidence = float(prediction.get(self.model_name, 0.0))
        if confidence < self.threshold:
            return None
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=confidence,
            frame_index=self._frames_seen,
        )
