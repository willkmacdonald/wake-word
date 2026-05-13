from __future__ import annotations

from pathlib import Path

import numpy as np

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


def _first_match(model_dir: Path, pattern: str) -> str:
    matches = sorted(model_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no {pattern} found in {model_dir}")
    return str(matches[0])


class SherpaOnnxKeywordEngine:
    name = "sherpa-onnx"

    def __init__(self, spotter: object, phrase_track: str) -> None:
        self.spotter = spotter
        self.phrase_track = phrase_track
        self.stream = spotter.create_stream()
        self._frames_seen = 0

    @classmethod
    def from_model_dir(
        cls,
        model_dir: str | Path,
        keywords_file: str | Path,
        phrase_track: str = "builtin-baseline",
        num_threads: int = 2,
        provider: str = "cpu",
    ) -> SherpaOnnxKeywordEngine:
        import sherpa_onnx

        model_dir = Path(model_dir)
        if not model_dir.is_dir():
            raise FileNotFoundError(f"sherpa-onnx model directory not found: {model_dir}")

        keywords_file = Path(keywords_file)
        if not keywords_file.is_file():
            raise FileNotFoundError(f"sherpa-onnx keywords file not found: {keywords_file}")

        spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(model_dir / "tokens.txt"),
            encoder=_first_match(model_dir, "encoder*.onnx"),
            decoder=_first_match(model_dir, "decoder*.onnx"),
            joiner=_first_match(model_dir, "joiner*.onnx"),
            num_threads=num_threads,
            keywords_file=str(keywords_file),
            provider=provider,
        )
        return cls(spotter=spotter, phrase_track=phrase_track)

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        if frame.channels != 1:
            raise ValueError(f"sherpa-onnx requires mono audio; got {frame.channels} channels")

        self._frames_seen += 1
        pcm = np.frombuffer(frame.pcm, dtype=np.int16).astype(np.float32) / 32768.0
        self.stream.accept_waveform(frame.sample_rate_hz, pcm)

        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)

        result = self.spotter.get_result(self.stream)
        if not result:
            return None

        self.spotter.reset_stream(self.stream)
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )
