import { describe, expect, it } from "vitest";
import { parseHelloMessage, transcriptPartial } from "../src/protocol.js";

describe("protocol", () => {
  it("parses a hello message", () => {
    const hello = parseHelloMessage({
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
    });

    expect(hello.endpointId).toBe("mac-studio-01");
    expect(hello.audio.sampleRateHz).toBe(16000);
  });

  it("serializes transcript partial events", () => {
    expect(transcriptPartial("session-001", "scalpel", 320)).toEqual({
      type: "transcript.partial",
      sessionId: "session-001",
      text: "scalpel",
      offsetMs: 320
    });
  });
});
