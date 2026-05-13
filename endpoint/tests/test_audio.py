import pytest
from wake_word_endpoint.audio import AudioFrame, GeneratedAudioSource, MicrophoneAudioSource


def test_audio_frame_20ms_size_for_16khz_mono_pcm():
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=20)

    assert frame.sample_rate_hz == 16000
    assert frame.channels == 1
    assert frame.duration_ms == 20
    assert len(frame.pcm) == 640


def test_generated_audio_source_yields_expected_number_of_frames():
    source = GeneratedAudioSource(sample_rate_hz=16000, channels=1, frame_duration_ms=20)

    frames = list(source.frames(max_frames=3))

    assert len(frames) == 3
    assert all(isinstance(frame, AudioFrame) for frame in frames)


class FakeRawInputStream:
    reads = [
        (b"bad", True),
        (b"\x00\x00" * 320, False),
        (b"\x01\x00" * 320, False),
    ]

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _frame_samples):
        return self.reads.pop(0)


def test_microphone_audio_source_skips_overflowed_frames_by_default(monkeypatch):
    FakeRawInputStream.reads = [
        (b"bad", True),
        (b"\x00\x00" * 320, False),
        (b"\x01\x00" * 320, False),
    ]

    class FakeSoundDevice:
        RawInputStream = FakeRawInputStream

    monkeypatch.setitem(__import__("sys").modules, "sounddevice", FakeSoundDevice)
    source = MicrophoneAudioSource(
        device=None,
        sample_rate_hz=16000,
        channels=1,
        frame_duration_ms=20,
    )

    frames = list(source.frames(max_frames=2))

    assert len(frames) == 2
    assert source.overflow_count == 1
    assert frames[0].pcm == b"\x00\x00" * 320


def test_microphone_audio_source_can_fail_on_overflow(monkeypatch):
    FakeRawInputStream.reads = [(b"bad", True)]

    class FakeSoundDevice:
        RawInputStream = FakeRawInputStream

    monkeypatch.setitem(__import__("sys").modules, "sounddevice", FakeSoundDevice)
    source = MicrophoneAudioSource(
        device=None,
        sample_rate_hz=16000,
        channels=1,
        frame_duration_ms=20,
        overflow_policy="raise",
    )

    with pytest.raises(RuntimeError, match="microphone input overflowed"):
        list(source.frames(max_frames=1))
