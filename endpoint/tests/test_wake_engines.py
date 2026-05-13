import numpy as np
import pytest
from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine
from wake_word_endpoint.wake_engines.openwakeword import OpenWakeWordEngine
from wake_word_endpoint.wake_engines.porcupine import PorcupineEngine
from wake_word_endpoint.wake_engines.sherpa_onnx import SherpaOnnxKeywordEngine


def test_fake_wake_engine_triggers_after_configured_frame_count():
    engine = FakeWakeEngine(trigger_after_frames=3)
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=20)

    assert engine.process(frame) is None
    assert engine.process(frame) is None
    event = engine.process(frame)

    assert event is not None
    assert event.engine == "fake"
    assert event.phrase_track == "builtin-baseline"
    assert event.confidence == 1.0


class FakeOpenWakeWordModel:
    def __init__(self) -> None:
        self.calls = 0

    def predict(self, pcm):
        self.calls += 1
        return {"hey_assistant": 0.9 if self.calls == 2 else 0.1}


def test_openwakeword_adapter_triggers_above_threshold():
    engine = OpenWakeWordEngine(
        model=FakeOpenWakeWordModel(),
        model_name="hey_assistant",
        phrase_track="builtin-baseline",
        threshold=0.8,
    )
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=80)

    assert engine.process(frame) is None
    event = engine.process(frame)

    assert event is not None
    assert event.engine == "openwakeword"
    assert event.confidence == 0.9


class FakeSherpaStream:
    def __init__(self) -> None:
        self.accepted_sample_rate = None
        self.accepted_samples = None

    def accept_waveform(self, sample_rate, samples):
        self.accepted_sample_rate = sample_rate
        self.accepted_samples = samples


class FakeSherpaSpotter:
    def __init__(self) -> None:
        self.stream = FakeSherpaStream()
        self.ready_calls = 0
        self.decoded = False
        self.reset_called = False

    def create_stream(self):
        return self.stream

    def is_ready(self, stream):
        assert stream is self.stream
        self.ready_calls += 1
        return self.ready_calls == 1

    def decode_stream(self, stream):
        assert stream is self.stream
        self.decoded = True

    def get_result(self, stream):
        assert stream is self.stream
        return "HEY SENTINEL" if self.decoded else ""

    def reset_stream(self, stream):
        assert stream is self.stream
        self.reset_called = True


def test_sherpa_onnx_adapter_streams_float_audio_and_triggers():
    spotter = FakeSherpaSpotter()
    engine = SherpaOnnxKeywordEngine(
        spotter=spotter,
        phrase_track="sherpa-baseline",
    )
    pcm = np.array([0, 32767, -32768], dtype=np.int16).tobytes()
    frame = AudioFrame(pcm=pcm, sample_rate_hz=16000, channels=1, duration_ms=20)

    event = engine.process(frame)

    assert event is not None
    assert event.engine == "sherpa-onnx"
    assert event.phrase_track == "sherpa-baseline"
    assert event.confidence == 1.0
    assert event.frame_index == 1
    assert spotter.stream.accepted_sample_rate == 16000
    np.testing.assert_allclose(
        spotter.stream.accepted_samples,
        np.array([0.0, 32767 / 32768, -1.0], dtype=np.float32),
    )
    assert spotter.reset_called is True


class FakePorcupine:
    sample_rate = 16000
    frame_length = 512

    def __init__(self) -> None:
        self.calls = 0
        self.last_pcm = None

    def process(self, pcm):
        self.calls += 1
        self.last_pcm = pcm
        return 0 if self.calls == 2 else -1


def _porcupine_sized_frame(sample_rate_hz: int = 16000, channels: int = 1) -> AudioFrame:
    pcm = np.zeros(FakePorcupine.frame_length * channels, dtype=np.int16).tobytes()
    return AudioFrame(
        pcm=pcm,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        duration_ms=32,
    )


def test_porcupine_adapter_triggers_on_keyword_index():
    engine = PorcupineEngine(
        porcupine=FakePorcupine(),
        keyword_names=["hey_or_assistant"],
        phrase_track="surgical-domain",
    )
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=32)

    assert engine.process(frame) is None
    event = engine.process(frame)

    assert event is not None
    assert event.engine == "porcupine"
    assert event.phrase_track == "surgical-domain"
    assert event.confidence == 1.0
    assert isinstance(engine.porcupine.last_pcm, np.ndarray)
    assert engine.porcupine.last_pcm.dtype == np.int16
    assert engine.porcupine.last_pcm.shape == (engine.porcupine.frame_length,)


def test_porcupine_adapter_rejects_wrong_frame_length():
    porcupine = FakePorcupine()
    engine = PorcupineEngine(
        porcupine=porcupine,
        keyword_names=["hey_or_assistant"],
        phrase_track="surgical-domain",
    )
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=20)

    with pytest.raises(ValueError, match="512 samples"):
        engine.process(frame)

    assert porcupine.calls == 0


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (_porcupine_sized_frame(sample_rate_hz=8000), "16000 Hz"),
        (_porcupine_sized_frame(channels=2), "mono audio"),
    ],
)
def test_porcupine_adapter_rejects_incompatible_audio_metadata(frame: AudioFrame, message: str):
    porcupine = FakePorcupine()
    engine = PorcupineEngine(
        porcupine=porcupine,
        keyword_names=["hey_or_assistant"],
        phrase_track="surgical-domain",
    )

    with pytest.raises(ValueError, match=message):
        engine.process(frame)

    assert porcupine.calls == 0
