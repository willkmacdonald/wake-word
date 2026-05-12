export const PROTOCOL_VERSION = "wake-word.v1";

export type AudioSpec = {
  format: "pcm_s16le";
  sampleRateHz: number;
  channels: number;
  frameDurationMs: number;
};

export type WakeSpec = {
  engine: string;
  phraseTrack: string;
};

export type HelloMessage = {
  type: "hello";
  protocolVersion: typeof PROTOCOL_VERSION;
  endpointId: string;
  endpointType: string;
  runId: string;
  audio: AudioSpec;
  wake: WakeSpec;
  startedAt: string;
};

export type TranscriptEvent = {
  type: "transcript.partial" | "transcript.final";
  sessionId: string;
  text: string;
  offsetMs: number;
};

function requireNonEmptyString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${field} is required`);
  }
  return value;
}

export function parseHelloMessage(value: unknown): HelloMessage {
  if (!value || typeof value !== "object") {
    throw new Error("hello message must be an object");
  }
  const payload = value as Record<string, unknown>;
  if (payload.type !== "hello") {
    throw new Error("first client message must be hello");
  }
  if (payload.protocolVersion !== PROTOCOL_VERSION) {
    throw new Error(`unsupported protocol version: ${String(payload.protocolVersion)}`);
  }
  if (!payload.audio || typeof payload.audio !== "object") {
    throw new Error("audio is required");
  }
  const audio = payload.audio as Record<string, unknown>;
  if (
    audio.format !== "pcm_s16le" ||
    audio.sampleRateHz !== 16000 ||
    audio.channels !== 1 ||
    audio.frameDurationMs !== 20
  ) {
    throw new Error("only 16 kHz mono pcm_s16le is accepted");
  }

  if (!payload.wake || typeof payload.wake !== "object") {
    throw new Error("wake is required");
  }
  const wake = payload.wake as Record<string, unknown>;

  return {
    type: "hello",
    protocolVersion: PROTOCOL_VERSION,
    endpointId: requireNonEmptyString(payload.endpointId, "endpointId"),
    endpointType: requireNonEmptyString(payload.endpointType, "endpointType"),
    runId: requireNonEmptyString(payload.runId, "runId"),
    audio: {
      format: "pcm_s16le",
      sampleRateHz: 16000,
      channels: 1,
      frameDurationMs: 20
    },
    wake: {
      engine: requireNonEmptyString(wake.engine, "wake.engine"),
      phraseTrack: requireNonEmptyString(wake.phraseTrack, "wake.phraseTrack")
    },
    startedAt: requireNonEmptyString(payload.startedAt, "startedAt")
  };
}

export function sessionAccepted(sessionId: string, maxSessionSeconds = 60) {
  return {
    type: "session.accepted",
    sessionId,
    maxSessionSeconds,
    acceptedAudio: {
      format: "pcm_s16le",
      sampleRateHz: 16000,
      channels: 1
    }
  };
}

export function transcriptPartial(sessionId: string, text: string, offsetMs: number): TranscriptEvent {
  return { type: "transcript.partial", sessionId, text, offsetMs };
}

export function transcriptFinal(sessionId: string, text: string, offsetMs: number): TranscriptEvent {
  return { type: "transcript.final", sessionId, text, offsetMs };
}

export function errorMessage(message: string) {
  return { type: "error", message };
}
