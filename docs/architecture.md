# Architecture

The architecture is endpoint -> controlled Azure gateway -> Microsoft transcription.

The endpoint streams no audio before local wake-word activation. After activation, it opens an authenticated websocket session to the gateway and sends post-trigger audio frames.

## Milestone 1 Verification

Milestone 1 verifies the architecture with a local mock gateway before Azure deployment:

```text
generated endpoint audio -> local fake wake engine -> websocket gateway session
-> mock transcription adapter -> transcript.final -> session.ended
```

The final local smoke test used run id `final-local-smoke` and produced
`session.accepted`, `transcript.final`, and `session.ended`. Accuracy metrics
remain live-observational only until a fixture-based evaluation lab is added.
