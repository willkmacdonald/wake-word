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

Run a local endpoint with a fake wake engine against a gateway mock, then add the Azure Speech adapter and Container Apps deployment files for the cloud gateway path.

## Local Gateway Smoke Test

Terminal 1:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token GATEWAY_ALLOWED_ENDPOINT_IDS=mac-studio-01 TRANSCRIPTION_MODE=mock npm run dev
```

Terminal 2:

```bash
. .venv/bin/activate
wake-endpoint run-fake endpoint/configs/mac.example.yaml --token dev-token --run-id local-fake-001
```

Expected: the endpoint prints `session.accepted`, `transcript.final`, and `session.ended`.

## Local Microphone Run

After the local gateway is running, the real endpoint path uses the microphone
and the wake engine selected in config:

```bash
. .venv/bin/activate
export GATEWAY_DEVICE_TOKEN=dev-token
wake-endpoint run endpoint/configs/mac.example.yaml --run-id local-mic-001 --max-listen-seconds 30
```

With the example config this uses the `fake` wake engine against live microphone
capture. Change `wake_word.engine` to `openwakeword` or `porcupine` after
installing the matching optional dependency to test real wake-word engines.

## Milestone 1 Status

Implemented:

- endpoint/gateway protocol contract
- Python endpoint config, microphone run command, audio source, fake wake engine, gateway client, and controller
- TypeScript gateway websocket server with auth and mock transcription
- Azure Speech adapter and Container Apps deployment files
- Raspberry Pi 5 bring-up docs and audio check script
- OpenWakeWord and Porcupine adapter wrappers
- live-trial observational report format
- gateway retry policy, negative protocol tests, Pi audio profiling, and basic gateway metrics
- gateway fail-closed token config, endpoint allow-list, and session duration/idle limits

Verified on May 12, 2026:

- Python tests
- gateway tests and typecheck
- local fake endpoint to mock gateway smoke test
- Mac microphone probe when USB mic is attached
- gateway `/healthz` and `/metrics` when running locally

Not yet verified:

- live Azure Container Apps deployment
- live Azure Speech transcription path
- Raspberry Pi 5 microphone capture after fresh setup
