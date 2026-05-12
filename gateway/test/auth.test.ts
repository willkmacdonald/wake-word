import { describe, expect, it } from "vitest";
import { authenticate } from "../src/auth.js";

describe("authenticate", () => {
  it("accepts a matching bearer token and endpoint id", () => {
    const result = authenticate({
      authorization: "Bearer dev-token",
      endpointId: "mac-studio-01",
      expectedToken: "dev-token"
    });

    expect(result.ok).toBe(true);
  });

  it("rejects a missing token", () => {
    const result = authenticate({
      authorization: undefined,
      endpointId: "mac-studio-01",
      expectedToken: "dev-token"
    });

    expect(result.ok).toBe(false);
  });

  it("rejects endpoint ids outside the allow list", () => {
    const result = authenticate({
      authorization: "Bearer dev-token",
      endpointId: "unknown-endpoint",
      expectedToken: "dev-token",
      allowedEndpointIds: ["mac-studio-01", "wakepi-01"]
    });

    expect(result).toEqual({ ok: false, reason: "endpoint id is not allowed" });
  });
});
