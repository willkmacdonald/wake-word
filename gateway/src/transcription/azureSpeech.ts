import * as sdk from "microsoft-cognitiveservices-speech-sdk";
import { transcriptFinal, transcriptPartial } from "../protocol.js";
import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

function cancellationError(event: { errorCode?: unknown; errorDetails?: unknown; reason?: unknown }): Error {
  const details = typeof event.errorDetails === "string" && event.errorDetails.length > 0 ? event.errorDetails : undefined;
  const code = typeof event.errorCode === "string" && event.errorCode.length > 0 ? event.errorCode : undefined;
  const reason = typeof event.reason === "string" && event.reason.length > 0 ? event.reason : undefined;
  const message = [code ?? reason, details].filter(Boolean).join(": ");
  return new Error(`Azure Speech recognition canceled${message ? `: ${message}` : ""}`);
}

export class AzureSpeechAdapter implements TranscriptionAdapter {
  constructor(private readonly options: { key: string; region: string }) {}

  async start(
    sessionId: string,
    onEvent: (event: ReturnType<typeof transcriptPartial> | ReturnType<typeof transcriptFinal>) => void
  ): Promise<TranscriptionSession> {
    if (!this.options.key || !this.options.region) {
      throw new Error("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required");
    }

    const speechConfig = sdk.SpeechConfig.fromSubscription(this.options.key, this.options.region);
    speechConfig.speechRecognitionLanguage = "en-US";

    const audioFormat = sdk.AudioStreamFormat.getWaveFormatPCM(16000, 16, 1);
    const pushStream = sdk.AudioInputStream.createPushStream(audioFormat);
    const audioConfig = sdk.AudioConfig.fromStreamInput(pushStream);
    const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);
    let canceledError: Error | undefined;

    recognizer.recognizing = (_sender, event) => {
      const text = event.result.text;
      if (text) {
        onEvent(transcriptPartial(sessionId, text, Number(event.result.offset) / 10000));
      }
    };

    recognizer.recognized = (_sender, event) => {
      const text = event.result.text;
      if (text) {
        onEvent(transcriptFinal(sessionId, text, Number(event.result.offset) / 10000));
      }
    };

    recognizer.canceled = (_sender, event) => {
      canceledError = cancellationError(event);
    };

    try {
      await new Promise<void>((resolve, reject) => {
        recognizer.startContinuousRecognitionAsync(resolve, reject);
      });
    } catch (error) {
      pushStream.close();
      recognizer.close();
      throw error;
    }

    let stopPromise: Promise<void> | undefined;

    return {
      pushAudio(chunk: Buffer) {
        if (canceledError) {
          throw canceledError;
        }
        const audioChunk = new ArrayBuffer(chunk.byteLength);
        new Uint8Array(audioChunk).set(chunk);
        pushStream.write(audioChunk);
      },
      async stop() {
        stopPromise ??= (async () => {
          pushStream.close();
          try {
            await new Promise<void>((resolve, reject) => {
              recognizer.stopContinuousRecognitionAsync(resolve, reject);
            });
          } finally {
            recognizer.close();
          }
        })();
        return stopPromise;
      }
    };
  }
}
