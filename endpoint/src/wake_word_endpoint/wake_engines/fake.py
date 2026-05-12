from __future__ import annotations

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class FakeWakeEngine:
    name = "fake"
    phrase_track = "builtin-baseline"

    def __init__(self, trigger_after_frames: int = 10) -> None:
        self.trigger_after_frames = trigger_after_frames
        self._frames_seen = 0
        self._triggered = False

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        self._frames_seen += 1
        if self._triggered or self._frames_seen < self.trigger_after_frames:
            return None
        self._triggered = True
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )
