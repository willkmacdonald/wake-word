import { describe, expect, it } from "vitest";
import { AzureSpeechAdapter } from "../src/transcription/azureSpeech.js";

describe("AzureSpeechAdapter", () => {
  it("rejects missing Azure credentials", async () => {
    const adapter = new AzureSpeechAdapter({ key: "", region: "" });

    await expect(adapter.start("session-001", () => undefined)).rejects.toThrow(
      "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required"
    );
  });
});
