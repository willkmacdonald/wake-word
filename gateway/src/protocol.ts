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
  const audio = payload.audio as Record<string, unknown>;
  const wake = payload.wake as Record<string, unknown>;
  if (!audio || audio.format !== "pcm_s16le" || audio.sampleRateHz !== 16000 || audio.channels !== 1) {
    throw new Error("only 16 kHz mono pcm_s16le is accepted");
  }
  if (typeof payload.endpointId !== "string" || payload.endpointId.length === 0) {
    throw new Error("endpointId is required");
  }
  return payload as HelloMessage;
}

export function sessionAccepted(sessionId: string) {
  return {
    type: "session.accepted",
    sessionId,
    maxSessionSeconds: 60,
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
