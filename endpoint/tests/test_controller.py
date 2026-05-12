import asyncio

from wake_word_endpoint.audio import GeneratedAudioSource
from wake_word_endpoint.controller import EndpointController
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine


class RecordingGateway:
    def __init__(self) -> None:
        self.streamed_frames = 0

    async def stream_session(self, hello, frames, stop_reason="manual"):
        async for _frame in frames:
            self.streamed_frames += 1
        return []


def test_controller_streams_only_after_wake_detection():
    source = GeneratedAudioSource(sample_rate_hz=16000, channels=1, frame_duration_ms=20)
    engine = FakeWakeEngine(trigger_after_frames=3)
    gateway = RecordingGateway()
    controller = EndpointController(
        endpoint_id="mac-studio-01",
        endpoint_type="mac-studio",
        run_id="run-001",
        audio_source=source,
        wake_engine=engine,
        gateway_client=gateway,
        sample_rate_hz=16000,
        channels=1,
        frame_duration_ms=20,
        max_stream_frames=5,
    )

    asyncio.run(controller.run_once(max_listen_frames=20))

    assert gateway.streamed_frames == 5
