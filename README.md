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
- `ROADMAP.md` — current project roadmap and phase gates.

## Wake Engine

The endpoint uses **Microsoft Azure custom keyword** for wake-word detection.
A `fake` engine is also wired up for deterministic smoke tests.

| Engine      | Install extra                       | Notes                                  |
|-------------|-------------------------------------|----------------------------------------|
| `fake`                       | none                               | Deterministic trigger for smoke tests  |
| `microsoft-custom-keyword`   | `uv sync --extra microsoft-keyword` | Azure custom keyword `.table` models   |

Set `wake_word.engine` in the endpoint config to choose between them.

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

## Local Hey Computer Demo

This is the Mac Studio demo path we used for the successful Phase 1 baseline.
It runs local wake detection with Microsoft Custom Keyword and uses the local
mock gateway, so no Azure transcription cost is incurred during the demo.

Prerequisites:

- USB microphone attached to the Mac Studio.
- Microsoft Custom Keyword model at
  `models/microsoft-custom-keyword/hey-computer.table`.
- Endpoint dependency installed with `uv sync --extra microsoft-keyword`.
- Gateway dependencies installed with `cd gateway && npm install`.

Terminal 1, from the repo root:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token \
GATEWAY_ALLOWED_ENDPOINT_IDS=mac-studio-01 \
TRANSCRIPTION_MODE=mock \
npm run dev
```

Terminal 2, from the repo root:

```bash
GATEWAY_DEVICE_TOKEN=dev-token \
uv run wake-endpoint run endpoint/configs/mac.microsoft-hey-computer.example.yaml \
  --run-id mac-microsoft-hey-computer-demo-001 \
  --max-listen-seconds 45 \
  --microsoft-keyword-table models/microsoft-custom-keyword/hey-computer.table
```

Run procedure:

1. Wait about two seconds after pressing enter.
2. Say `Hey Computer` once.
3. Watch for the `wake.detected` line. That is the local wake-detection moment.
4. Wait for `session.accepted`, `transcript.final`, and `session.ended`.

Expected behavior:

- `wake.detected` should appear immediately after the wake phrase.
- The mock transcript appears later because the current config streams a fixed
  five second post-trigger clip before finalizing.
- A visible response around the seven second mark is expected in this mock path
  and is not wake-detection latency.

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
Use `endpoint/configs/mac.microsoft-hey-computer.example.yaml` with
`--microsoft-keyword-table models/microsoft-custom-keyword/hey-computer.table`
to run the current Azure custom keyword baseline. Each detection prints a
`wake.detected` line immediately.

## Live Wake-Word Trial

The active wake-word trial lives under `eval/live_trials/`:

- Microsoft Azure custom keyword — "Hey Computer"

Render the summary with `wake-eval-report summarize eval/live_trials/<file>.yaml`.

## Milestone 1 Status

Implemented:

- endpoint/gateway protocol contract
- Python endpoint config, microphone run command, audio source, fake wake
  engine, gateway client, and controller
- TypeScript gateway websocket server with auth and mock transcription
- Azure Speech adapter and Container Apps deployment files
- Raspberry Pi 5 bring-up docs and audio check script
- Microsoft Azure custom keyword adapter
- live-trial observational report format with one recorded run
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
- live Microsoft Azure custom keyword trial on Mac Studio

Not yet verified:

- live Azure Container Apps deployment
- live Azure Speech transcription path
- Raspberry Pi 5 microphone capture after fresh setup
