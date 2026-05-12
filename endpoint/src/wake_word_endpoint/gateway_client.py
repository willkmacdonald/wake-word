from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class GatewayRetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be positive")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError(
                "max_delay_seconds must be greater than or equal to base_delay_seconds"
            )
        if self.jitter_ratio < 0:
            raise ValueError("jitter_ratio must not be negative")

    def delay_for_attempt(self, attempt: int) -> float:
        base_delay = min(self.max_delay_seconds, self.base_delay_seconds * (2**attempt))
        jitter = (
            0.0 if self.jitter_ratio == 0 else random.uniform(0.0, base_delay * self.jitter_ratio)
        )
        return min(self.max_delay_seconds, base_delay + jitter)


class GatewayConnectionError(RuntimeError):
    def __init__(self, endpoint_id: str, attempts: int, reason: str) -> None:
        super().__init__(
            f"gateway connection failed for endpoint {endpoint_id} after {attempts} "
            f"attempts: {reason}"
        )


class GatewayClient:
    def __init__(
        self,
        url: str,
        endpoint_id: str,
        token: str,
        retry_policy: GatewayRetryPolicy | None = None,
    ) -> None:
        self.url = url
        self.endpoint_id = endpoint_id
        self.token = token
        self.retry_policy = retry_policy or GatewayRetryPolicy()

    async def stream_session(
        self,
        hello: SessionHello,
        frames: AsyncIterator[AudioFrame],
        stop_reason: str = "manual",
    ) -> list[ServerMessage]:
        websocket, events = await self._connect_and_accept(hello)
        try:
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
        except (OSError, TimeoutError, websockets.exceptions.WebSocketException) as error:
            raise GatewayConnectionError(
                self.endpoint_id,
                attempts=1,
                reason=f"active stream interrupted: {error}",
            ) from error
        finally:
            await websocket.close()
        return events

    async def _connect_and_accept(self, hello: SessionHello) -> tuple[Any, list[ServerMessage]]:
        last_error: Exception | None = None
        for attempt in range(self.retry_policy.max_attempts):
            websocket: Any | None = None
            try:
                headers = GatewayHeaders(
                    endpoint_id=self.endpoint_id,
                    token=self.token,
                ).to_headers()
                websocket = await websockets.connect(self.url, additional_headers=headers)
                await websocket.send(hello.to_json())
                accepted_raw = await websocket.recv()
                if not isinstance(accepted_raw, str):
                    raise RuntimeError("gateway accepted response must be JSON text")
                try:
                    accepted = parse_server_message(accepted_raw)
                except ValueError as error:
                    raise RuntimeError(f"gateway accepted response is invalid: {error}") from error
                if accepted.type != "session.accepted":
                    raise RuntimeError(
                        f"gateway first event must be session.accepted, got {accepted.type}"
                    )
                return websocket, [accepted]
            except (OSError, TimeoutError, websockets.exceptions.WebSocketException) as error:
                last_error = error
                if websocket is not None:
                    await websocket.close()
                if attempt == self.retry_policy.max_attempts - 1:
                    break
                await asyncio.sleep(self.retry_policy.delay_for_attempt(attempt))
            except Exception:
                if websocket is not None:
                    await websocket.close()
                raise
        reason = str(last_error) if last_error else "unknown error"
        raise GatewayConnectionError(self.endpoint_id, self.retry_policy.max_attempts, reason)
