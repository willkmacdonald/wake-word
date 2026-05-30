# Wake-Word Endpoint

Local wake-word detection for a surgical-suite-shaped ambient-listening system.
The endpoint listens locally and streams nothing until a wake word fires. Cloud
credentials live in the gateway, never on the endpoint.

```text
USB mic → Mac Studio or Raspberry Pi 5 endpoint → local wake-word detection
        → post-trigger websocket stream → Azure-hosted gateway
        → Microsoft transcription → live transcript events
```

## Repo Areas

- `endpoint/` — Python endpoint for Mac Studio and Raspberry Pi 5.
- `gateway/` — TypeScript gateway service for endpoint streams and Azure transcription.
- `eval/` — live-trial reporting for observational wake-word comparisons.
- `docs/` — architecture, hardware, protocol, and evaluation notes.

## Wake Engines

The endpoint ships with four interchangeable wake engines, selected via
`wake_word.engine` in the endpoint config:

| Engine            | Install extra              | Notes                                          |
|-------------------|----------------------------|------------------------------------------------|
| `fake`            | none                       | Deterministic trigger for smoke tests          |
| `openwakeword`    | `pip install .[openwakeword]` | ONNX models, "Hey Jarvis" out of the box   |
| `porcupine`       | `pip install .[porcupine]` | Picovoice, requires access key                 |
| `sherpa`          | `pip install .[sherpa]`    | Local keyword spotting, custom keyword lists   |
| `microsoft`       | `pip install .[microsoft-keyword]` | Azure custom keyword `.table` models   |

## First Milestone

Run a local endpoint with a fake wake engine against a gateway mock, then add
the Azure Speech adapter and Container Apps deployment files for the cloud
gateway path.

## Local Gateway Smoke Test

Terminal 1:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token \
GATEWAY_ALLOWED_ENDPOINT_IDS=mac-studio-01 \
TRANSCRIPTION_MODE=mock \
npm run dev
```

Terminal 2:

```bash
. .venv/bin/activate
wake-endpoint run-fake endpoint/configs/mac.example.yaml \
  --token dev-token --run-id local-fake-001
```

Expected: the endpoint prints `session.accepted`, `transcript.final`, and
`session.ended`.

## Local Microphone Run

After the local gateway is running, the real endpoint path uses the microphone
and the wake engine selected in config:

```bash
. .venv/bin/activate
export GATEWAY_DEVICE_TOKEN=dev-token
wake-endpoint run endpoint/configs/mac.example.yaml \
  --run-id local-mic-001 --max-listen-seconds 30
```

The example config uses the `fake` engine against live microphone capture.
Change `wake_word.engine` to `openwakeword`, `porcupine`, `sherpa`, or
`microsoft` after installing the matching optional dependency to test real
wake-word engines. Each detection prints its trigger latency.

## Live Wake-Word Trials

Observational reports for each engine live under `eval/live_trials/`. The
current set covers four runs from May 2026:

- OpenWakeWord — "Hey Jarvis"
- Sherpa-ONNX — "Hey Computer"
- Sherpa-ONNX — "Wake Up Atlas"
- Microsoft Azure custom keyword — "Hey Computer"

Render a trial summary with `wake-eval-report eval/live_trials/<file>.yaml`.

## Milestone 1 Status

Implemented:

- endpoint/gateway protocol contract
- Python endpoint config, microphone run command, audio source, fake wake
  engine, gateway client, and controller
- TypeScript gateway websocket server with auth and mock transcription
- Azure Speech adapter and Container Apps deployment files
- Raspberry Pi 5 bring-up docs and audio check script
- OpenWakeWord, Porcupine, Sherpa-ONNX, and Microsoft custom keyword adapters
- live-trial observational report format with four recorded runs
- gateway retry policy, negative protocol tests, Pi audio profiling, basic
  gateway metrics
- gateway fail-closed token config, endpoint allow-list, and session
  duration/idle limits
- microphone input-overflow tolerance and wake-detection latency print-out

Verified on May 16, 2026:

- Python tests
- gateway tests and typecheck
- local fake endpoint to mock gateway smoke test
- Mac microphone probe when USB mic is attached
- gateway `/healthz` and `/metrics` when running locally
- four live wake-word trials on Mac Studio

Not yet verified:

- live Azure Container Apps deployment
- live Azure Speech transcription path
- Raspberry Pi 5 microphone capture after fresh setup
