from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine
from wake_word_endpoint.wake_engines.openwakeword import OpenWakeWordEngine


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
