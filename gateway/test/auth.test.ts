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
});
