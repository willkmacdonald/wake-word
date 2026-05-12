import asyncio
from collections.abc import Iterator

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.controller import EndpointController
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine


class TrackingAudioSource:
    def __init__(self) -> None:
        self.yielded_count = 0

    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        while max_frames is None or self.yielded_count < max_frames:
            self.yielded_count += 1
            yield AudioFrame(
                pcm=self.yielded_count.to_bytes(2, "little"),
                sample_rate_hz=16000,
                channels=1,
                duration_ms=20,
            )


class RecordingGateway:
    def __init__(self, source: TrackingAudioSource) -> None:
        self.source = source
        self.entry_yielded_count: int | None = None
        self.streamed_markers: list[int] = []
        self.streamed_frames = 0

    async def stream_session(self, hello, frames, stop_reason="manual"):
        self.entry_yielded_count = self.source.yielded_count
        async for frame in frames:
            self.streamed_markers.append(int.from_bytes(frame.pcm, "little"))
            self.streamed_frames += 1
        return []


def test_controller_streams_only_after_wake_detection():
    source = TrackingAudioSource()
    engine = FakeWakeEngine(trigger_after_frames=3)
    gateway = RecordingGateway(source)
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

    asyncio.run(controller.run_once(max_listen_frames=3))

    assert gateway.entry_yielded_count == 3
    assert gateway.streamed_frames == 5
    assert gateway.streamed_markers == [4, 5, 6, 7, 8]
