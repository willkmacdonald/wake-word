import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

export class AzureSpeechAdapter implements TranscriptionAdapter {
  constructor(private readonly options: { key: string; region: string }) {}

  async start(): Promise<TranscriptionSession> {
    if (!this.options.key || !this.options.region) {
      throw new Error("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required in azure mode");
    }
    throw new Error("Azure transcription mode is unavailable in the mock gateway checkpoint");
  }
}
