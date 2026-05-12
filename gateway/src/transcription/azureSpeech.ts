import * as sdk from "microsoft-cognitiveservices-speech-sdk";
import { transcriptFinal, transcriptPartial } from "../protocol.js";
import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

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

    await new Promise<void>((resolve, reject) => {
      recognizer.startContinuousRecognitionAsync(resolve, reject);
    });

    return {
      pushAudio(chunk: Buffer) {
        const audioChunk = new ArrayBuffer(chunk.byteLength);
        new Uint8Array(audioChunk).set(chunk);
        pushStream.write(audioChunk);
      },
      async stop() {
        pushStream.close();
        await new Promise<void>((resolve, reject) => {
          recognizer.stopContinuousRecognitionAsync(resolve, reject);
        });
        recognizer.close();
      }
    };
  }
}
