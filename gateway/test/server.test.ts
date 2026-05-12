import { once } from "node:events";
import { AddressInfo } from "node:net";
import { describe, expect, it } from "vitest";
import WebSocket from "ws";
import { buildServer } from "../src/server.js";
import { TranscriptionAdapter } from "../src/transcription/types.js";

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

function helloMessage() {
  return {
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
  };
}

async function withTimeout<T>(promise: Promise<T>, message: string) {
  let timeout: NodeJS.Timeout | undefined;
  try {
    return await Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        timeout = setTimeout(() => reject(new Error(message)), 250);
      })
    ]);
  } finally {
    if (timeout) {
      clearTimeout(timeout);
    }
  }
}

describe("gateway server", () => {
  it("serves gateway metrics", async () => {
    const app = buildServer({ deviceToken: "dev-token", transcriptionMode: "mock" });

    try {
      const response = await app.inject({ method: "GET", url: "/metrics" });

      expect(response.statusCode).toBe(200);
      expect(response.headers["content-type"]).toContain("text/plain");
      expect(response.body).toContain("wake_word_gateway_sessions_started_total 0");
    } finally {
      await app.close();
    }
  });

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
    ws.send(JSON.stringify(helloMessage()));
    const accepted = await nextMessage();
    ws.send(Buffer.alloc(640));
    ws.send(JSON.stringify({ type: "stop", reason: "manual" }));
    const transcript = await nextMessage();
    const ended = await nextMessage();

    expect(accepted.type).toBe("session.accepted");
    expect(transcript.type).toBe("transcript.final");
    expect(ended.type).toBe("session.ended");
    const metrics = await app.inject({ method: "GET", url: "/metrics" });
    expect(metrics.body).toContain("wake_word_gateway_sessions_started_total 1");
    expect(metrics.body).toContain("wake_word_gateway_sessions_ended_total 1");

    ws.close();
    await app.close();
  });

  it("stops a started transcription session when the client closes before stop", async () => {
    let stopCalls = 0;
    let resolveStopped: (() => void) | undefined;
    const stopped = new Promise<void>((resolve) => {
      resolveStopped = resolve;
    });
    const transcriptionAdapter: TranscriptionAdapter = {
      async start() {
        return {
          pushAudio() {},
          async stop() {
            stopCalls += 1;
            resolveStopped?.();
          }
        };
      }
    };

    const app = buildServer({
      deviceToken: "dev-token",
      transcriptionMode: "mock",
      transcriptionAdapter
    });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });
    const nextMessage = collectJsonMessages(ws);

    try {
      await once(ws, "open");
      ws.send(JSON.stringify(helloMessage()));
      const accepted = await nextMessage();
      expect(accepted.type).toBe("session.accepted");

      ws.close();

      await withTimeout(stopped, "session was not stopped after client close");
      expect(stopCalls).toBe(1);
      const metrics = await app.inject({ method: "GET", url: "/metrics" });
      expect(metrics.body).toContain("wake_word_gateway_sessions_started_total 1");
      expect(metrics.body).toContain("wake_word_gateway_sessions_ended_total 1");
    } finally {
      ws.close();
      await app.close();
    }
  });

  it("ends sessions that exceed the configured max duration", async () => {
    let stopCalls = 0;
    const transcriptionAdapter: TranscriptionAdapter = {
      async start() {
        return {
          pushAudio() {},
          async stop() {
            stopCalls += 1;
          }
        };
      }
    };

    const app = buildServer({
      deviceToken: "dev-token",
      transcriptionMode: "mock",
      transcriptionAdapter,
      maxSessionSeconds: 0.01,
      idleTimeoutSeconds: 1
    });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });
    const nextMessage = collectJsonMessages(ws);

    try {
      await once(ws, "open");
      ws.send(JSON.stringify(helloMessage()));
      const accepted = await nextMessage();
      const ended = await withTimeout(nextMessage(), "max duration did not end session");

      expect(accepted.type).toBe("session.accepted");
      expect(ended).toEqual({
        type: "session.ended",
        sessionId: accepted.sessionId,
        reason: "max_duration"
      });
      expect(stopCalls).toBe(1);
    } finally {
      ws.close();
      await app.close();
    }
  });

  it("ends sessions that stop sending audio before the idle timeout", async () => {
    let stopCalls = 0;
    const transcriptionAdapter: TranscriptionAdapter = {
      async start() {
        return {
          pushAudio() {},
          async stop() {
            stopCalls += 1;
          }
        };
      }
    };

    const app = buildServer({
      deviceToken: "dev-token",
      transcriptionMode: "mock",
      transcriptionAdapter,
      maxSessionSeconds: 1,
      idleTimeoutSeconds: 0.01
    });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });
    const nextMessage = collectJsonMessages(ws);

    try {
      await once(ws, "open");
      ws.send(JSON.stringify(helloMessage()));
      const accepted = await nextMessage();
      const ended = await withTimeout(nextMessage(), "idle timeout did not end session");

      expect(accepted.type).toBe("session.accepted");
      expect(ended).toEqual({
        type: "session.ended",
        sessionId: accepted.sessionId,
        reason: "idle_timeout"
      });
      expect(stopCalls).toBe(1);
    } finally {
      ws.close();
      await app.close();
    }
  });

  it("stops a session that starts after the client has already closed", async () => {
    let resolveStart: (() => void) | undefined;
    let resolveStartCalled: (() => void) | undefined;
    const startCalled = new Promise<void>((resolve) => {
      resolveStartCalled = resolve;
    });
    let stopCalls = 0;
    let resolveStopped: (() => void) | undefined;
    const stopped = new Promise<void>((resolve) => {
      resolveStopped = resolve;
    });
    const transcriptionAdapter: TranscriptionAdapter = {
      async start() {
        resolveStartCalled?.();
        await new Promise<void>((resolve) => {
          resolveStart = resolve;
        });
        return {
          pushAudio() {},
          async stop() {
            stopCalls += 1;
            resolveStopped?.();
          }
        };
      }
    };

    const app = buildServer({
      deviceToken: "dev-token",
      transcriptionMode: "mock",
      transcriptionAdapter
    });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });

    try {
      await once(ws, "open");
      ws.send(JSON.stringify(helloMessage()));
      await withTimeout(startCalled, "transcription start was not called");

      ws.close();
      await withTimeout(once(ws, "close"), "client websocket did not close");
      resolveStart?.();

      await withTimeout(stopped, "session was not stopped after delayed start resolved");
      expect(stopCalls).toBe(1);
    } finally {
      ws.close();
      await app.close();
    }
  });

  it("rejects invalid endpoint tokens", async () => {
    const app = buildServer({ deviceToken: "dev-token", transcriptionMode: "mock" });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer wrong-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });
    const nextMessage = collectJsonMessages(ws);

    try {
      await once(ws, "open");
      const error = await nextMessage();

      expect(error.type).toBe("error");
      expect(error.message).toBe("invalid bearer token");
      const metrics = await app.inject({ method: "GET", url: "/metrics" });
      expect(metrics.body).toContain("wake_word_gateway_errors_total 1");
    } finally {
      ws.close();
      await app.close();
    }
  });

  it("rejects endpoint ids outside the configured allow list", async () => {
    const app = buildServer({
      deviceToken: "dev-token",
      transcriptionMode: "mock",
      allowedEndpointIds: ["wakepi-01"]
    });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });
    const nextMessage = collectJsonMessages(ws);

    try {
      await once(ws, "open");
      const error = await nextMessage();

      expect(error.type).toBe("error");
      expect(error.message).toBe("endpoint id is not allowed");
    } finally {
      ws.close();
      await app.close();
    }
  });

  it("returns an error for malformed hello messages", async () => {
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

    try {
      await once(ws, "open");
      ws.send(JSON.stringify({ type: "hello", protocolVersion: "wrong" }));
      const error = await nextMessage();

      expect(error.type).toBe("error");
      expect(error.message).toContain("unsupported protocol version");
    } finally {
      ws.close();
      await app.close();
    }
  });
});
