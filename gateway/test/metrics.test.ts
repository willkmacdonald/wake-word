import { describe, expect, it } from "vitest";
import { GatewayMetrics } from "../src/metrics.js";

describe("GatewayMetrics", () => {
  it("renders Prometheus-style counters", () => {
    const metrics = new GatewayMetrics();
    metrics.recordSessionStarted();
    metrics.recordSessionEnded();
    metrics.recordError();

    const text = metrics.render();

    expect(text).toContain("wake_word_gateway_sessions_started_total 1");
    expect(text).toContain("wake_word_gateway_sessions_ended_total 1");
    expect(text).toContain("wake_word_gateway_errors_total 1");
  });
});
