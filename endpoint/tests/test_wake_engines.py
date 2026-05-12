from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine


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
