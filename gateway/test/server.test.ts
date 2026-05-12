import { once } from "node:events";
import { AddressInfo } from "node:net";
import { describe, expect, it } from "vitest";
import WebSocket from "ws";
import { buildServer } from "../src/server.js";

function collectJsonMessages(ws: WebSocket) {
  const messages: string[] = [];
  const waiters: Array<(value: string) => void> = [];

  ws.on("message", (data) => {
    const text = data.toString();
    const waiter = waiters.shift();
    if (waiter) {
      waiter(text);
      return;
    }
    messages.push(text);
  });

  return async () => {
    const text =
      messages.shift() ??
      (await new Promise<string>((resolve) => {
        waiters.push(resolve);
      }));
    return JSON.parse(text);
  };
}

describe("gateway server", () => {
  it("accepts hello, binary audio, stop, and returns transcript events", async () => {
    const app = buildServer({ deviceToken: "dev-token", transcriptionMode: "mock" });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });
    const nextMessage = collectJsonMessages(ws);

    await once(ws, "open");
    ws.send(
      JSON.stringify({
        type: "hello",
        protocolVersion: "wake-word.v1",
        endpointId: "mac-studio-01",
        endpointType: "mac-studio",
        runId: "run-001",
        audio: {
          format: "pcm_s16le",
          sampleRateHz: 16000,
          channels: 1,
          frameDurationMs: 20
        },
        wake: {
          engine: "fake",
          phraseTrack: "builtin-baseline"
        },
        startedAt: "2026-05-11T18:00:00Z"
      })
    );
    const accepted = await nextMessage();
    ws.send(Buffer.alloc(640));
    ws.send(JSON.stringify({ type: "stop", reason: "manual" }));
    const transcript = await nextMessage();
    const ended = await nextMessage();

    expect(accepted.type).toBe("session.accepted");
    expect(transcript.type).toBe("transcript.final");
    expect(ended.type).toBe("session.ended");

    ws.close();
    await app.close();
  });
});
