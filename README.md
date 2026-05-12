# Wake-Word Exploration

This repo explores local wake-word detection for a surgical-suite-shaped ambient-listening system.

The first demo path is:

```text
USB mic -> Mac Studio or Raspberry Pi 5 endpoint -> local wake-word detection
-> post-trigger websocket stream -> Azure-hosted gateway -> Microsoft transcription
-> live transcript events
```

The endpoint must not stream audio before local wake-word activation. Azure credentials belong in the gateway, not on the endpoint.

## Repo Areas

- `endpoint/`: Python endpoint for Mac Studio and Raspberry Pi 5.
- `gateway/`: TypeScript gateway service for endpoint streams and Azure transcription.
- `eval/`: live-trial reporting for observational wake-word comparisons.
- `docs/`: architecture, hardware, protocol, and evaluation notes.

## First Milestone

Run a local endpoint with a fake wake engine against a gateway mock, then replace the mock transcription adapter with Azure Speech and deploy the gateway to Azure Container Apps.

## Local Gateway Smoke Test

Terminal 1:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token TRANSCRIPTION_MODE=mock npm run dev
```

Terminal 2:

```bash
. .venv/bin/activate
wake-endpoint run-fake endpoint/configs/mac.example.yaml --token dev-token --run-id local-fake-001
```

Expected: the endpoint prints `session.accepted`, `transcript.final`, and `session.ended`.
