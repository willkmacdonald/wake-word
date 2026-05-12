import { describe, expect, it } from "vitest";
import { parseAllowedEndpointIds, readRuntimeConfig } from "../src/config.js";

describe("runtime config", () => {
  it("fails closed when the gateway token is missing", () => {
    expect(() => readRuntimeConfig({})).toThrow("GATEWAY_DEVICE_TOKEN is required");
  });

  it("parses allowed endpoint ids", () => {
    expect(parseAllowedEndpointIds("mac-studio-01, wakepi-01,,")).toEqual([
      "mac-studio-01",
      "wakepi-01"
    ]);
  });

  it("reads gateway runtime config from environment", () => {
    expect(
      readRuntimeConfig({
        GATEWAY_DEVICE_TOKEN: "secret-token",
        TRANSCRIPTION_MODE: "azure",
        GATEWAY_ALLOWED_ENDPOINT_IDS: "mac-studio-01,wakepi-01"
      })
    ).toEqual({
      port: 8080,
      host: "0.0.0.0",
      deviceToken: "secret-token",
      transcriptionMode: "azure",
      allowedEndpointIds: ["mac-studio-01", "wakepi-01"]
    });
  });
});
