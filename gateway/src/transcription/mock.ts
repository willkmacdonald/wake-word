import { TranscriptEvent, transcriptFinal } from "../protocol.js";
import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

export class MockTranscriptionAdapter implements TranscriptionAdapter {
  async start(sessionId: string, onEvent: (event: TranscriptEvent) => void) {
    let bytes = 0;
    return {
      pushAudio(chunk: Buffer) {
        bytes += chunk.length;
      },
      async stop() {
        onEvent(transcriptFinal(sessionId, `mock transcript from ${bytes} bytes`, 0));
      }
    } satisfies TranscriptionSession;
  }
}
