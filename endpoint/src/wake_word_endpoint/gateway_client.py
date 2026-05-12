from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import websockets

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.protocol import (
    ClientStop,
    ServerMessage,
    SessionHello,
    parse_server_message,
)


@dataclass(frozen=True)
class GatewayHeaders:
    endpoint_id: str
    token: str

    def to_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Endpoint-Id": self.endpoint_id,
        }


class GatewayClient:
    def __init__(self, url: str, endpoint_id: str, token: str) -> None:
        self.url = url
        self.endpoint_id = endpoint_id
        self.token = token

    async def stream_session(
        self,
        hello: SessionHello,
        frames: AsyncIterator[AudioFrame],
        stop_reason: str = "manual",
    ) -> list[ServerMessage]:
        events: list[ServerMessage] = []
        headers = GatewayHeaders(endpoint_id=self.endpoint_id, token=self.token).to_headers()
        async with websockets.connect(self.url, additional_headers=headers) as websocket:
            await websocket.send(hello.to_json())
            accepted_raw = await websocket.recv()
            if not isinstance(accepted_raw, str):
                raise RuntimeError("gateway accepted response must be JSON text")
            accepted = parse_server_message(accepted_raw)
            events.append(accepted)
            async for frame in frames:
                await websocket.send(frame.pcm)
            await websocket.send(ClientStop(reason=stop_reason).to_json())
            while True:
                raw = await websocket.recv()
                if not isinstance(raw, str):
                    raise RuntimeError("gateway event must be JSON text")
                event = parse_server_message(raw)
                events.append(event)
                if event.type in {"session.ended", "error"}:
                    break
        return events
