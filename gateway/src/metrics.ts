export class GatewayMetrics {
  private sessionsStarted = 0;
  private sessionsEnded = 0;
  private errors = 0;

  recordSessionStarted() {
    this.sessionsStarted += 1;
  }

  recordSessionEnded() {
    this.sessionsEnded += 1;
  }

  recordError() {
    this.errors += 1;
  }

  render() {
    return [
      "# TYPE wake_word_gateway_sessions_started_total counter",
      `wake_word_gateway_sessions_started_total ${this.sessionsStarted}`,
      "# TYPE wake_word_gateway_sessions_ended_total counter",
      `wake_word_gateway_sessions_ended_total ${this.sessionsEnded}`,
      "# TYPE wake_word_gateway_errors_total counter",
      `wake_word_gateway_errors_total ${this.errors}`,
      ""
    ].join("\n");
  }
}
