from __future__ import annotations

from pathlib import Path
from threading import Lock

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class MicrosoftCustomKeywordEngine:
    name = "microsoft-custom-keyword"

    def __init__(
        self,
        keyword_model: object,
        recognizer: object,
        push_stream: object,
        phrase_track: str,
        sample_rate_hz: int = 16000,
        channels: int = 1,
    ) -> None:
        self.keyword_model = keyword_model
        self.recognizer = recognizer
        self.push_stream = push_stream
        self.phrase_track = phrase_track
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self._frames_seen = 0
        self._recognized = False
        self._canceled_message: str | None = None
        self._lock = Lock()

        self.recognizer.recognized.connect(self._on_recognized)
        self.recognizer.canceled.connect(self._on_canceled)
        self._recognition_future = self.recognizer.recognize_once_async(self.keyword_model)

    @classmethod
    def from_table_file(
        cls,
        table_file: str | Path,
        phrase_track: str = "custom-keyword",
        sample_rate_hz: int = 16000,
        channels: int = 1,
    ) -> MicrosoftCustomKeywordEngine:
        import azure.cognitiveservices.speech as speechsdk

        table_file = Path(table_file)
        if not table_file.is_file():
            raise FileNotFoundError(f"Microsoft Custom Keyword .table file not found: {table_file}")
        if channels != 1:
            raise ValueError(
                f"Microsoft Custom Keyword requires mono audio; got {channels} channels"
            )

        stream_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=sample_rate_hz,
            bits_per_sample=16,
            channels=channels,
        )
        push_stream = speechsdk.audio.PushAudioInputStream(stream_format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        keyword_model = speechsdk.KeywordRecognitionModel(str(table_file))
        recognizer = speechsdk.KeywordRecognizer(audio_config=audio_config)
        return cls(
            keyword_model=keyword_model,
            recognizer=recognizer,
            push_stream=push_stream,
            phrase_track=phrase_track,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
        )

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        if frame.sample_rate_hz != self.sample_rate_hz:
            raise ValueError(
                "Microsoft Custom Keyword requires "
                f"{self.sample_rate_hz} Hz audio; got {frame.sample_rate_hz} Hz"
            )
        if frame.channels != self.channels:
            raise ValueError(
                "Microsoft Custom Keyword requires "
                f"{self.channels} channel audio; got {frame.channels} channels"
            )

        self._frames_seen += 1
        self.push_stream.write(frame.pcm)

        with self._lock:
            if self._canceled_message:
                raise RuntimeError(
                    f"Microsoft Custom Keyword recognition canceled: {self._canceled_message}"
                )
            if not self._recognized:
                return None
            self._recognized = False

        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )

    def _on_recognized(self, _event: object) -> None:
        with self._lock:
            self._recognized = True

    def _on_canceled(self, event: object) -> None:
        with self._lock:
            self._canceled_message = _event_message(event)


def _event_message(event: object) -> str:
    if event is None:
        return "unknown cancellation"
    result = getattr(event, "result", None)
    if result is not None:
        cancellation_details = getattr(result, "cancellation_details", None)
        if cancellation_details is not None:
            error_details = getattr(cancellation_details, "error_details", None)
            if error_details:
                return str(error_details)
            reason = getattr(cancellation_details, "reason", None)
            if reason:
                return str(reason)
    return str(event)
