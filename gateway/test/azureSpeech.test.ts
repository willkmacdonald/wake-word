import { beforeEach, describe, expect, it, vi } from "vitest";
import { AzureSpeechAdapter } from "../src/transcription/azureSpeech.js";

const sdkMock = vi.hoisted(() => {
  const pushStreams: MockPushStream[] = [];
  const recognizers: MockSpeechRecognizer[] = [];

  class MockPushStream {
    writes: ArrayBuffer[] = [];
    closed = false;

    write(chunk: ArrayBuffer) {
      this.writes.push(chunk);
    }

    close() {
      this.closed = true;
    }
  }

  class MockSpeechRecognizer {
    static startError: Error | undefined;
    static stopError: Error | undefined;

    recognizing:
      | ((_sender: MockSpeechRecognizer, event: { result: { text: string; offset: number } }) => void)
      | undefined;
    recognized:
      | ((_sender: MockSpeechRecognizer, event: { result: { text: string; offset: number } }) => void)
      | undefined;
    canceled:
      | ((_sender: MockSpeechRecognizer, event: { errorCode?: string; errorDetails?: string; reason?: string }) => void)
      | undefined;
    closed = false;
    stopCalls = 0;

    constructor() {
      recognizers.push(this);
    }

    startContinuousRecognitionAsync(resolve: () => void, reject: (error: Error) => void) {
      if (MockSpeechRecognizer.startError) {
        reject(MockSpeechRecognizer.startError);
        return;
      }
      resolve();
    }

    stopContinuousRecognitionAsync(resolve: () => void, reject: (error: Error) => void) {
      this.stopCalls += 1;
      if (MockSpeechRecognizer.stopError) {
        reject(MockSpeechRecognizer.stopError);
        return;
      }
      resolve();
    }

    close() {
      this.closed = true;
    }
  }

  return {
    pushStreams,
    recognizers,
    MockSpeechRecognizer,
    SpeechConfig: {
      fromSubscription: vi.fn(() => ({ speechRecognitionLanguage: "" }))
    },
    AudioStreamFormat: {
      getWaveFormatPCM: vi.fn(() => ({ format: "pcm" }))
    },
    AudioInputStream: {
      createPushStream: vi.fn(() => {
        const stream = new MockPushStream();
        pushStreams.push(stream);
        return stream;
      })
    },
    AudioConfig: {
      fromStreamInput: vi.fn((stream: MockPushStream) => ({ stream }))
    },
    SpeechRecognizer: MockSpeechRecognizer
  };
});

vi.mock("microsoft-cognitiveservices-speech-sdk", () => sdkMock);

describe("AzureSpeechAdapter", () => {
  beforeEach(() => {
    sdkMock.pushStreams.length = 0;
    sdkMock.recognizers.length = 0;
    sdkMock.MockSpeechRecognizer.startError = undefined;
    sdkMock.MockSpeechRecognizer.stopError = undefined;
    vi.clearAllMocks();
  });

  it("rejects missing Azure credentials", async () => {
    const adapter = new AzureSpeechAdapter({ key: "", region: "" });

    await expect(adapter.start("session-001", () => undefined)).rejects.toThrow(
      "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required"
    );
  });

  it("cleans up stream and recognizer when startup fails after SDK objects are created", async () => {
    sdkMock.MockSpeechRecognizer.startError = new Error("startup failed");
    const adapter = new AzureSpeechAdapter({ key: "key", region: "region" });

    await expect(adapter.start("session-001", () => undefined)).rejects.toThrow("startup failed");

    expect(sdkMock.pushStreams).toHaveLength(1);
    expect(sdkMock.recognizers).toHaveLength(1);
    expect(sdkMock.pushStreams[0].closed).toBe(true);
    expect(sdkMock.recognizers[0].closed).toBe(true);
  });

  it("closes the recognizer when stop recognition rejects", async () => {
    const adapter = new AzureSpeechAdapter({ key: "key", region: "region" });
    const session = await adapter.start("session-001", () => undefined);
    sdkMock.MockSpeechRecognizer.stopError = new Error("stop failed");

    await expect(session.stop()).rejects.toThrow("stop failed");

    expect(sdkMock.pushStreams[0].closed).toBe(true);
    expect(sdkMock.recognizers[0].closed).toBe(true);
  });

  it("only stops the recognizer once when stop is called repeatedly", async () => {
    const adapter = new AzureSpeechAdapter({ key: "key", region: "region" });
    const session = await adapter.start("session-001", () => undefined);

    await session.stop();
    await session.stop();

    expect(sdkMock.recognizers[0].stopCalls).toBe(1);
  });

  it("emits partial and final transcript events from SDK recognition callbacks", async () => {
    const onEvent = vi.fn();
    const adapter = new AzureSpeechAdapter({ key: "key", region: "region" });

    await adapter.start("session-001", onEvent);
    sdkMock.recognizers[0].recognizing?.(sdkMock.recognizers[0], {
      result: { text: "part", offset: 120000 }
    });
    sdkMock.recognizers[0].recognized?.(sdkMock.recognizers[0], {
      result: { text: "final", offset: 340000 }
    });

    expect(onEvent).toHaveBeenCalledWith({
      type: "transcript.partial",
      sessionId: "session-001",
      text: "part",
      offsetMs: 12
    });
    expect(onEvent).toHaveBeenCalledWith({
      type: "transcript.final",
      sessionId: "session-001",
      text: "final",
      offsetMs: 34
    });
  });

  it("surfaces SDK cancellation on the next audio push", async () => {
    const adapter = new AzureSpeechAdapter({ key: "key", region: "region" });
    const session = await adapter.start("session-001", () => undefined);

    sdkMock.recognizers[0].canceled?.(sdkMock.recognizers[0], {
      errorCode: "AuthenticationFailure",
      errorDetails: "invalid subscription key"
    });

    expect(() => session.pushAudio(Buffer.from([1, 2, 3]))).toThrow(
      "Azure Speech recognition canceled: AuthenticationFailure: invalid subscription key"
    );
  });

  it("copies buffer chunks before writing to the Azure push stream", async () => {
    const adapter = new AzureSpeechAdapter({ key: "key", region: "region" });
    const session = await adapter.start("session-001", () => undefined);
    const chunk = Buffer.from([1, 2, 3]);

    session.pushAudio(chunk);
    chunk.fill(9);

    expect(Array.from(new Uint8Array(sdkMock.pushStreams[0].writes[0]))).toEqual([1, 2, 3]);
  });
});
