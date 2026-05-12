from wake_word_endpoint.audio import AudioFrame, GeneratedAudioSource


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
