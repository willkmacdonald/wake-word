import { TranscriptEvent } from "../protocol.js";

export type TranscriptionAdapter = {
  start(sessionId: string, onEvent: (event: TranscriptEvent) => void): Promise<TranscriptionSession>;
};

export type TranscriptionSession = {
  pushAudio(chunk: Buffer): void;
  stop(): Promise<void>;
};
