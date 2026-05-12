from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiveTrial:
    run_id: str
    endpoint_type: str
    microphone: str
    wake_engine: str
    phrase_track: str
    false_accepts: int
    missed_detections: int
    trigger_to_first_transcript_ms: int | None
    notes: str
