from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from wake_word_endpoint.audio import AudioFrame


@dataclass(frozen=True)
class WakeDetection:
    engine: str
    phrase_track: str
    confidence: float
    frame_index: int


class WakeEngine(Protocol):
    name: str
    phrase_track: str

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        """Return a detection event when the wake phrase is detected."""
