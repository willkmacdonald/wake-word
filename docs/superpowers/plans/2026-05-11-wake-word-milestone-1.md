# Wake-Word Milestone 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-shaped demo path: local Mac/Pi endpoint detects a wake event locally, streams only post-trigger audio to an Azure-hosted gateway, and receives live transcript events.

**Architecture:** The endpoint is a Python package with microphone capture, wake-word engine plugins, a session controller, and a websocket gateway client. The gateway is a TypeScript/Node service hosted in Azure Container Apps, with authentication/session policy at the gateway and Azure Speech integration behind a transcription adapter. Evaluation tooling records observational live-trial metrics for Mac Studio and Raspberry Pi 5 runs using the same USB microphone sequentially.

**Tech Stack:** Python 3.11+, pytest, sounddevice/PortAudio, websockets, psutil, PyYAML, optional OpenWakeWord and Picovoice Porcupine adapters; Node 20+, TypeScript, Fastify, `@fastify/websocket`, Vitest, Azure Speech SDK for JavaScript, Azure Container Apps.

---

## Scope

This plan implements the approved design spec in `docs/superpowers/specs/2026-05-11-wake-word-design.md` through these checkpoints:

- Checkpoint A: repo scaffold, protocol contract, and tests.
- Checkpoint B: local endpoint session controller with a fake wake engine and generated audio source.
- Checkpoint C: gateway websocket server with a mock transcription adapter.
- Checkpoint D: endpoint-to-gateway local integration test proving no pre-trigger streaming.
- Checkpoint E: Azure Speech adapter and Azure Container Apps deployment files.
- Checkpoint F: Raspberry Pi 5 bring-up script/docs.
- Checkpoint G: first OpenWakeWord and Porcupine plugin adapters behind the same engine interface.
- Checkpoint H: live trial reporting for observational Mac/Pi comparison.
- Checkpoint I: review-driven hardening for network failures, negative tests, Pi audio profiling, Azure latency posture, and explicit next-phase evaluation work.

Clinical note generation, EHR integration, HIPAA claims, simultaneous Mac/Pi microphone comparison, and recorded fixture evaluation remain out of scope.

## External Review Disposition

An external LLM reviewed this plan before execution. Incorporate the valid findings without expanding Milestone 1 into a full reproducible audio lab.

Accepted into Milestone 1:

- Add endpoint gateway retry/backoff behavior and explicit gateway connection failure errors.
- Add negative tests for gateway authentication, malformed hello messages, and gateway client retry policy.
- Add Raspberry Pi audio profiling and ALSA/CoreAudio difference notes so Mac/Pi comparisons do not assume identical audio behavior.
- Keep Azure Container Apps `minReplicas: 1` and document it as a latency choice, then verify `/healthz` and trigger-to-first-transcript latency during milestone verification.
- Add lightweight gateway metrics for session and error counts.

Deferred to the next evaluation milestone:

- Recorded fixture library with positive phrases, negative samples, silence, and noise overlays.
- SNR/noisy-environment test curves for surgical-suite-like conditions.
- Audio preprocessing experiments such as gain control, high-pass filtering, and noise suppression.

Rejected for Milestone 1:

- Replacing websocket audio transport with RTP, UDP, or gRPC. WebSocket remains the first endpoint/gateway transport because it combines control and post-trigger audio in one authenticated channel and is adequate for validating the architecture.
- Generalizing the audio contract beyond 16 kHz mono PCM. Milestone 1 keeps 16 kHz, mono, signed 16-bit little-endian PCM as the explicit contract. Resampling and format negotiation belong in a later compatibility milestone.

## File Structure

Create this structure:

```text
.
├── README.md
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── azure-gateway.md
│   ├── hardware.md
│   ├── protocol.md
│   ├── wake-word-evaluation.md
│   └── superpowers/
│       ├── specs/2026-05-11-wake-word-design.md
│       └── plans/2026-05-11-wake-word-milestone-1.md
├── endpoint/
│   ├── README.md
│   ├── configs/
│   │   ├── mac.example.yaml
│   │   └── pi.example.yaml
│   ├── src/wake_word_endpoint/
│   │   ├── __init__.py
│   │   ├── audio.py
│   │   ├── cli.py
│   │   ├── config.py
│   │   ├── controller.py
│   │   ├── gateway_client.py
│   │   ├── protocol.py
│   │   └── wake_engines/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── fake.py
│   │       ├── openwakeword.py
│   │       └── porcupine.py
│   └── tests/
│       ├── test_audio.py
│       ├── test_config.py
│       ├── test_controller.py
│       ├── test_gateway_client.py
│       ├── test_protocol.py
│       └── test_wake_engines.py
├── eval/
│   ├── README.md
│   ├── live_trial_template.yaml
│   ├── src/wake_word_eval/
│   │   ├── __init__.py
│   │   ├── report.py
│   │   └── trial.py
│   └── tests/test_report.py
├── gateway/
│   ├── README.md
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── auth.ts
│   │   ├── index.ts
│   │   ├── protocol.ts
│   │   ├── server.ts
│   │   └── transcription/
│   │       ├── azureSpeech.ts
│   │       ├── mock.ts
│   │       └── types.ts
│   └── test/
│       ├── auth.test.ts
│       ├── protocol.test.ts
│       └── server.test.ts
├── infra/
│   ├── README.md
│   └── container-app.bicep
└── scripts/
    └── pi/
        └── check_audio.sh
```

## Task 1: Repository Scaffold And Tooling

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `pyproject.toml`
- Create: `endpoint/README.md`
- Create: `gateway/README.md`
- Create: `gateway/package.json`
- Create: `gateway/tsconfig.json`
- Create: `gateway/vitest.config.ts`
- Create: `gateway/src/index.ts`
- Create: `gateway/test/protocol.test.ts`
- Create: `eval/README.md`
- Create: `docs/architecture.md`
- Create: `docs/azure-gateway.md`
- Create: `docs/hardware.md`
- Create: `docs/wake-word-evaluation.md`

- [ ] **Step 1: Write the root scaffold files**

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.pyc
*.wav
*.log
node_modules/
dist/
coverage/
.env
.env.*
!.env.example
```

Create `README.md`:

```markdown
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
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.build_meta"

[project]
name = "wake-word-endpoint"
version = "0.1.0"
description = "Local wake-word endpoint and evaluation tooling"
requires-python = ">=3.11"
dependencies = [
  "numpy>=2.0.0",
  "psutil>=6.0.0",
  "PyYAML>=6.0.2",
  "rich>=13.9.0",
  "sounddevice>=0.5.0",
  "typer>=0.12.0",
  "websockets>=14.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "ruff>=0.8.0",
]
openwakeword = [
  "openwakeword>=0.6.0",
]
porcupine = [
  "pvporcupine>=3.0.0",
]

[project.scripts]
wake-endpoint = "wake_word_endpoint.cli:app"
wake-eval-report = "wake_word_eval.report:app"

[tool.setuptools.packages.find]
where = ["endpoint/src", "eval/src"]

[tool.pytest.ini_options]
testpaths = ["endpoint/tests", "eval/tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Write the gateway package scaffold**

Create `gateway/package.json`:

```json
{
  "name": "wake-word-gateway",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "dev": "tsx src/index.ts",
    "test": "vitest run",
    "typecheck": "tsc -p tsconfig.json --noEmit"
  },
  "dependencies": {
    "@fastify/websocket": "^11.0.0",
    "fastify": "^5.0.0",
    "microsoft-cognitiveservices-speech-sdk": "^1.44.0",
    "nanoid": "^5.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "tsx": "^4.19.0",
    "typescript": "^5.7.0",
    "vitest": "^2.1.0",
    "ws": "^8.18.0"
  },
  "engines": {
    "node": ">=20"
  }
}
```

Create `gateway/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src",
    "types": ["node"]
  },
  "include": ["src/**/*.ts"]
}
```

Create `gateway/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"]
  }
});
```

Create `gateway/src/index.ts`:

```ts
import { buildServer } from "./server.js";

const port = Number(process.env.PORT ?? "8080");
const host = process.env.HOST ?? "0.0.0.0";

const server = buildServer({
  deviceToken: process.env.GATEWAY_DEVICE_TOKEN ?? "dev-token",
  transcriptionMode: process.env.TRANSCRIPTION_MODE === "azure" ? "azure" : "mock"
});

await server.listen({ port, host });
console.log(`wake-word gateway listening on ${host}:${port}`);
```

Create `gateway/test/protocol.test.ts`:

```ts
import { describe, expect, it } from "vitest";

describe("gateway scaffold", () => {
  it("runs vitest", () => {
    expect(true).toBe(true);
  });
});
```

- [ ] **Step 3: Write initial README files**

Create `endpoint/README.md`:

```markdown
# Endpoint

The endpoint runs on the Mac Studio or Raspberry Pi 5. It owns microphone capture, local wake-word detection, post-trigger streaming, and local run metadata.

The endpoint does not own Azure Speech or Azure OpenAI credentials.
```

Create `gateway/README.md`:

```markdown
# Gateway

The gateway accepts authenticated post-trigger audio streams from endpoints, enforces session policy, and forwards audio to Microsoft transcription services.

Local development starts with `TRANSCRIPTION_MODE=mock`. Azure deployment uses `TRANSCRIPTION_MODE=azure`.
```

Create `eval/README.md`:

```markdown
# Evaluation

Evaluation tooling records observational live microphone trials. Early metrics are useful for comparing engines and endpoints, but they are not reproducible lab measurements.
```

Create `docs/architecture.md`:

```markdown
# Architecture

The architecture is endpoint -> controlled Azure gateway -> Microsoft transcription.

The endpoint streams no audio before local wake-word activation. After activation, it opens an authenticated websocket session to the gateway and sends post-trigger audio frames.
```

Create `docs/azure-gateway.md`:

```markdown
# Azure Gateway

The gateway is the only component that stores Microsoft transcription credentials. Endpoints authenticate to the gateway with device credentials.
```

Create `docs/hardware.md`:

```markdown
# Hardware

The first comparison uses one USB microphone sequentially:

1. Plug the microphone into the Mac Studio and run a live trial.
2. Move the same microphone to the Raspberry Pi 5 and run the same trial.

This keeps microphone hardware constant without requiring simultaneous capture.
```

Create `docs/wake-word-evaluation.md`:

```markdown
# Wake-Word Evaluation

The first evaluation mode is live microphone testing. Reports must mark metrics as observational because the input audio is not replayed from fixed fixtures.
```

- [ ] **Step 4: Run scaffold tests**

Run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
cd gateway
npm install
npm test
```

Expected:

```text
Python: no tests collected or all scaffold tests pass
Gateway: 1 test passes
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore README.md pyproject.toml endpoint gateway eval docs
git commit -m "chore: scaffold wake-word project"
```

## Task 2: Shared Protocol Contract

**Files:**
- Create: `docs/protocol.md`
- Create: `endpoint/src/wake_word_endpoint/__init__.py`
- Create: `endpoint/src/wake_word_endpoint/protocol.py`
- Create: `endpoint/tests/test_protocol.py`
- Create: `gateway/src/protocol.ts`
- Modify: `gateway/test/protocol.test.ts`

- [ ] **Step 1: Write failing Python protocol tests**

Create `endpoint/tests/test_protocol.py`:

```python
import json

from wake_word_endpoint.protocol import AudioSpec, SessionHello, WakeSpec, parse_server_message


def test_session_hello_serializes_to_gateway_contract():
    hello = SessionHello(
        endpoint_id="mac-studio-01",
        endpoint_type="mac-studio",
        run_id="run-001",
        audio=AudioSpec(sample_rate_hz=16000, channels=1, frame_duration_ms=20),
        wake=WakeSpec(engine="fake", phrase_track="builtin-baseline"),
        started_at="2026-05-11T18:00:00Z",
    )

    payload = json.loads(hello.to_json())

    assert payload == {
        "type": "hello",
        "protocolVersion": "wake-word.v1",
        "endpointId": "mac-studio-01",
        "endpointType": "mac-studio",
        "runId": "run-001",
        "audio": {
            "format": "pcm_s16le",
            "sampleRateHz": 16000,
            "channels": 1,
            "frameDurationMs": 20,
        },
        "wake": {
            "engine": "fake",
            "phraseTrack": "builtin-baseline",
        },
        "startedAt": "2026-05-11T18:00:00Z",
    }


def test_parse_transcript_event_from_gateway():
    event = parse_server_message(
        json.dumps(
            {
                "type": "transcript.partial",
                "sessionId": "session-001",
                "text": "scalpel",
                "offsetMs": 320,
            }
        )
    )

    assert event.type == "transcript.partial"
    assert event.session_id == "session-001"
    assert event.text == "scalpel"
    assert event.offset_ms == 320
```

- [ ] **Step 2: Run Python protocol tests and verify failure**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_protocol.py -q
```

Expected:

```text
FAIL with ModuleNotFoundError or ImportError for wake_word_endpoint.protocol
```

- [ ] **Step 3: Implement Python protocol model**

Create `endpoint/src/wake_word_endpoint/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `endpoint/src/wake_word_endpoint/protocol.py`:

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

PROTOCOL_VERSION = "wake-word.v1"


@dataclass(frozen=True)
class AudioSpec:
    sample_rate_hz: int
    channels: int
    frame_duration_ms: int
    format: str = "pcm_s16le"

    def to_wire(self) -> dict[str, int | str]:
        return {
            "format": self.format,
            "sampleRateHz": self.sample_rate_hz,
            "channels": self.channels,
            "frameDurationMs": self.frame_duration_ms,
        }


@dataclass(frozen=True)
class WakeSpec:
    engine: str
    phrase_track: str

    def to_wire(self) -> dict[str, str]:
        return {"engine": self.engine, "phraseTrack": self.phrase_track}


@dataclass(frozen=True)
class SessionHello:
    endpoint_id: str
    endpoint_type: str
    run_id: str
    audio: AudioSpec
    wake: WakeSpec
    started_at: str
    type: Literal["hello"] = "hello"
    protocol_version: str = PROTOCOL_VERSION

    def to_wire(self) -> dict[str, object]:
        return {
            "type": self.type,
            "protocolVersion": self.protocol_version,
            "endpointId": self.endpoint_id,
            "endpointType": self.endpoint_type,
            "runId": self.run_id,
            "audio": self.audio.to_wire(),
            "wake": self.wake.to_wire(),
            "startedAt": self.started_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_wire(), separators=(",", ":"))


@dataclass(frozen=True)
class ClientStop:
    reason: str
    type: Literal["stop"] = "stop"

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


@dataclass(frozen=True)
class ServerMessage:
    type: str
    session_id: str | None = None
    text: str | None = None
    offset_ms: int | None = None
    reason: str | None = None
    message: str | None = None


def parse_server_message(raw: str) -> ServerMessage:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("server message must be a JSON object")

    return ServerMessage(
        type=str(payload["type"]),
        session_id=payload.get("sessionId"),
        text=payload.get("text"),
        offset_ms=payload.get("offsetMs"),
        reason=payload.get("reason"),
        message=payload.get("message"),
    )
```

- [ ] **Step 4: Write gateway protocol tests**

Replace `gateway/test/protocol.test.ts` with:

```ts
import { describe, expect, it } from "vitest";
import { parseHelloMessage, transcriptPartial } from "../src/protocol.js";

describe("protocol", () => {
  it("parses a hello message", () => {
    const hello = parseHelloMessage({
      type: "hello",
      protocolVersion: "wake-word.v1",
      endpointId: "mac-studio-01",
      endpointType: "mac-studio",
      runId: "run-001",
      audio: {
        format: "pcm_s16le",
        sampleRateHz: 16000,
        channels: 1,
        frameDurationMs: 20
      },
      wake: {
        engine: "fake",
        phraseTrack: "builtin-baseline"
      },
      startedAt: "2026-05-11T18:00:00Z"
    });

    expect(hello.endpointId).toBe("mac-studio-01");
    expect(hello.audio.sampleRateHz).toBe(16000);
  });

  it("serializes transcript partial events", () => {
    expect(transcriptPartial("session-001", "scalpel", 320)).toEqual({
      type: "transcript.partial",
      sessionId: "session-001",
      text: "scalpel",
      offsetMs: 320
    });
  });
});
```

- [ ] **Step 5: Implement gateway protocol model**

Create `gateway/src/protocol.ts`:

```ts
export const PROTOCOL_VERSION = "wake-word.v1";

export type AudioSpec = {
  format: "pcm_s16le";
  sampleRateHz: number;
  channels: number;
  frameDurationMs: number;
};

export type WakeSpec = {
  engine: string;
  phraseTrack: string;
};

export type HelloMessage = {
  type: "hello";
  protocolVersion: typeof PROTOCOL_VERSION;
  endpointId: string;
  endpointType: string;
  runId: string;
  audio: AudioSpec;
  wake: WakeSpec;
  startedAt: string;
};

export type TranscriptEvent = {
  type: "transcript.partial" | "transcript.final";
  sessionId: string;
  text: string;
  offsetMs: number;
};

export function parseHelloMessage(value: unknown): HelloMessage {
  if (!value || typeof value !== "object") {
    throw new Error("hello message must be an object");
  }
  const payload = value as Record<string, unknown>;
  if (payload.type !== "hello") {
    throw new Error("first client message must be hello");
  }
  if (payload.protocolVersion !== PROTOCOL_VERSION) {
    throw new Error(`unsupported protocol version: ${String(payload.protocolVersion)}`);
  }
  const audio = payload.audio as Record<string, unknown>;
  const wake = payload.wake as Record<string, unknown>;
  if (!audio || audio.format !== "pcm_s16le" || audio.sampleRateHz !== 16000 || audio.channels !== 1) {
    throw new Error("only 16 kHz mono pcm_s16le is accepted");
  }
  if (typeof payload.endpointId !== "string" || payload.endpointId.length === 0) {
    throw new Error("endpointId is required");
  }
  return payload as HelloMessage;
}

export function sessionAccepted(sessionId: string) {
  return {
    type: "session.accepted",
    sessionId,
    maxSessionSeconds: 60,
    acceptedAudio: {
      format: "pcm_s16le",
      sampleRateHz: 16000,
      channels: 1
    }
  };
}

export function transcriptPartial(sessionId: string, text: string, offsetMs: number): TranscriptEvent {
  return { type: "transcript.partial", sessionId, text, offsetMs };
}

export function transcriptFinal(sessionId: string, text: string, offsetMs: number): TranscriptEvent {
  return { type: "transcript.final", sessionId, text, offsetMs };
}

export function errorMessage(message: string) {
  return { type: "error", message };
}
```

- [ ] **Step 6: Document the wire protocol**

Create `docs/protocol.md`:

```markdown
# Endpoint/Gateway Protocol

The endpoint opens an authenticated websocket to `/v1/audio`.

## Authentication

The endpoint sends:

```text
Authorization: Bearer dev-token
X-Endpoint-Id: mac-studio-01
```

Device tokens authenticate the endpoint to the gateway. Azure Speech credentials are never sent to endpoints.

## Client Hello

The first websocket message is JSON:

```json
{
  "type": "hello",
  "protocolVersion": "wake-word.v1",
  "endpointId": "mac-studio-01",
  "endpointType": "mac-studio",
  "runId": "run-001",
  "audio": {
    "format": "pcm_s16le",
    "sampleRateHz": 16000,
    "channels": 1,
    "frameDurationMs": 20
  },
  "wake": {
    "engine": "openwakeword",
    "phraseTrack": "builtin-baseline"
  },
  "startedAt": "2026-05-11T18:00:00Z"
}
```

## Audio Frames

After `session.accepted`, binary websocket messages contain raw 16 kHz mono signed 16-bit little-endian PCM audio. A 20 ms frame is 640 bytes.

## Server Events

```json
{ "type": "session.accepted", "sessionId": "session-001", "maxSessionSeconds": 60 }
```

```json
{ "type": "transcript.partial", "sessionId": "session-001", "text": "hello", "offsetMs": 320 }
```

```json
{ "type": "transcript.final", "sessionId": "session-001", "text": "hello world", "offsetMs": 900 }
```

## Stop

The endpoint sends a JSON stop message to end a session:

```json
{ "type": "stop", "reason": "manual" }
```
```

- [ ] **Step 7: Run protocol tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_protocol.py -q
cd gateway
npm test -- protocol.test.ts
```

Expected:

```text
Python protocol tests pass
Gateway protocol tests pass
```

- [ ] **Step 8: Commit**

```bash
git add docs/protocol.md endpoint/src/wake_word_endpoint endpoint/tests gateway/src/protocol.ts gateway/test/protocol.test.ts
git commit -m "feat: define endpoint gateway protocol"
```

## Task 3: Endpoint Configuration And CLI

**Files:**
- Create: `endpoint/src/wake_word_endpoint/config.py`
- Create: `endpoint/src/wake_word_endpoint/cli.py`
- Create: `endpoint/configs/mac.example.yaml`
- Create: `endpoint/configs/pi.example.yaml`
- Create: `endpoint/tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Create `endpoint/tests/test_config.py`:

```python
from pathlib import Path

from wake_word_endpoint.config import load_config


def test_loads_endpoint_config(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
endpoint:
  id: mac-studio-01
  type: mac-studio
microphone:
  device: null
  sample_rate_hz: 16000
  channels: 1
wake_word:
  engine: fake
  phrase_track: builtin-baseline
gateway:
  url: ws://localhost:8080/v1/audio
  token_env: GATEWAY_DEVICE_TOKEN
session:
  frame_duration_ms: 20
  max_seconds: 60
""".strip()
    )

    config = load_config(config_path)

    assert config.endpoint.id == "mac-studio-01"
    assert config.microphone.sample_rate_hz == 16000
    assert config.wake_word.engine == "fake"
    assert config.gateway.url == "ws://localhost:8080/v1/audio"
    assert config.session.frame_duration_ms == 20
```

- [ ] **Step 2: Run config test and verify failure**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_config.py -q
```

Expected:

```text
FAIL with ModuleNotFoundError or ImportError for wake_word_endpoint.config
```

- [ ] **Step 3: Implement config loading**

Create `endpoint/src/wake_word_endpoint/config.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EndpointConfig:
    id: str
    type: str


@dataclass(frozen=True)
class MicrophoneConfig:
    device: str | None
    sample_rate_hz: int
    channels: int


@dataclass(frozen=True)
class WakeWordConfig:
    engine: str
    phrase_track: str


@dataclass(frozen=True)
class GatewayConfig:
    url: str
    token_env: str


@dataclass(frozen=True)
class SessionConfig:
    frame_duration_ms: int
    max_seconds: int


@dataclass(frozen=True)
class AppConfig:
    endpoint: EndpointConfig
    microphone: MicrophoneConfig
    wake_word: WakeWordConfig
    gateway: GatewayConfig
    session: SessionConfig


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"missing config section: {name}")
    return value


def load_config(path: str | Path) -> AppConfig:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("config file must contain a mapping")

    endpoint = _section(data, "endpoint")
    microphone = _section(data, "microphone")
    wake_word = _section(data, "wake_word")
    gateway = _section(data, "gateway")
    session = _section(data, "session")

    return AppConfig(
        endpoint=EndpointConfig(id=str(endpoint["id"]), type=str(endpoint["type"])),
        microphone=MicrophoneConfig(
            device=microphone.get("device"),
            sample_rate_hz=int(microphone["sample_rate_hz"]),
            channels=int(microphone["channels"]),
        ),
        wake_word=WakeWordConfig(
            engine=str(wake_word["engine"]),
            phrase_track=str(wake_word["phrase_track"]),
        ),
        gateway=GatewayConfig(url=str(gateway["url"]), token_env=str(gateway["token_env"])),
        session=SessionConfig(
            frame_duration_ms=int(session["frame_duration_ms"]),
            max_seconds=int(session["max_seconds"]),
        ),
    )
```

- [ ] **Step 4: Add example endpoint configs**

Create `endpoint/configs/mac.example.yaml`:

```yaml
endpoint:
  id: mac-studio-01
  type: mac-studio
microphone:
  device: null
  sample_rate_hz: 16000
  channels: 1
wake_word:
  engine: fake
  phrase_track: builtin-baseline
gateway:
  url: ws://localhost:8080/v1/audio
  token_env: GATEWAY_DEVICE_TOKEN
session:
  frame_duration_ms: 20
  max_seconds: 60
```

Create `endpoint/configs/pi.example.yaml`:

```yaml
endpoint:
  id: wakepi-01
  type: raspberry-pi-5
microphone:
  device: null
  sample_rate_hz: 16000
  channels: 1
wake_word:
  engine: fake
  phrase_track: builtin-baseline
gateway:
  url: ws://localhost:8080/v1/audio
  token_env: GATEWAY_DEVICE_TOKEN
session:
  frame_duration_ms: 20
  max_seconds: 60
```

- [ ] **Step 5: Add CLI shell**

Create `endpoint/src/wake_word_endpoint/cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from wake_word_endpoint.config import load_config

app = typer.Typer(no_args_is_help=True)


@app.command()
def config_check(config: Path) -> None:
    """Load an endpoint config and print the effective endpoint identity."""
    loaded = load_config(config)
    print(
        {
            "endpoint_id": loaded.endpoint.id,
            "endpoint_type": loaded.endpoint.type,
            "wake_engine": loaded.wake_word.engine,
            "gateway_url": loaded.gateway.url,
        }
    )
```

- [ ] **Step 6: Run config tests and CLI check**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_config.py -q
wake-endpoint config-check endpoint/configs/mac.example.yaml
```

Expected:

```text
Config tests pass
CLI prints mac-studio-01, mac-studio, fake, and ws://localhost:8080/v1/audio
```

- [ ] **Step 7: Commit**

```bash
git add endpoint/src/wake_word_endpoint/config.py endpoint/src/wake_word_endpoint/cli.py endpoint/configs endpoint/tests/test_config.py
git commit -m "feat: add endpoint configuration"
```

## Task 4: Audio Sources And Microphone Probe

**Files:**
- Create: `endpoint/src/wake_word_endpoint/audio.py`
- Create: `endpoint/tests/test_audio.py`
- Modify: `endpoint/src/wake_word_endpoint/cli.py`

- [ ] **Step 1: Write failing audio tests**

Create `endpoint/tests/test_audio.py`:

```python
from wake_word_endpoint.audio import AudioFrame, GeneratedAudioSource


def test_audio_frame_20ms_size_for_16khz_mono_pcm():
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=20)

    assert frame.sample_rate_hz == 16000
    assert frame.channels == 1
    assert frame.duration_ms == 20
    assert len(frame.pcm) == 640


def test_generated_audio_source_yields_expected_number_of_frames():
    source = GeneratedAudioSource(sample_rate_hz=16000, channels=1, frame_duration_ms=20)

    frames = list(source.frames(max_frames=3))

    assert len(frames) == 3
    assert all(isinstance(frame, AudioFrame) for frame in frames)
```

- [ ] **Step 2: Run audio tests and verify failure**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_audio.py -q
```

Expected:

```text
FAIL with ModuleNotFoundError or ImportError for wake_word_endpoint.audio
```

- [ ] **Step 3: Implement audio abstractions**

Create `endpoint/src/wake_word_endpoint/audio.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class AudioFrame:
    pcm: bytes
    sample_rate_hz: int
    channels: int
    duration_ms: int

    @classmethod
    def pcm_silence(cls, sample_rate_hz: int, channels: int, duration_ms: int) -> "AudioFrame":
        samples = int(sample_rate_hz * duration_ms / 1000) * channels
        return cls(
            pcm=np.zeros(samples, dtype=np.int16).tobytes(),
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            duration_ms=duration_ms,
        )


class AudioSource(Protocol):
    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        """Yield PCM audio frames."""


class GeneratedAudioSource:
    def __init__(self, sample_rate_hz: int, channels: int, frame_duration_ms: int) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms

    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        emitted = 0
        while max_frames is None or emitted < max_frames:
            emitted += 1
            yield AudioFrame.pcm_silence(
                sample_rate_hz=self.sample_rate_hz,
                channels=self.channels,
                duration_ms=self.frame_duration_ms,
            )


class MicrophoneAudioSource:
    def __init__(
        self,
        device: str | int | None,
        sample_rate_hz: int,
        channels: int,
        frame_duration_ms: int,
    ) -> None:
        self.device = device
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms

    def frames(self, max_frames: int | None = None) -> Iterator[AudioFrame]:
        import sounddevice as sd

        frame_samples = int(self.sample_rate_hz * self.frame_duration_ms / 1000)
        emitted = 0
        with sd.RawInputStream(
            samplerate=self.sample_rate_hz,
            blocksize=frame_samples,
            device=self.device,
            channels=self.channels,
            dtype="int16",
        ) as stream:
            while max_frames is None or emitted < max_frames:
                data, overflowed = stream.read(frame_samples)
                if overflowed:
                    raise RuntimeError("microphone input overflowed")
                emitted += 1
                yield AudioFrame(
                    pcm=bytes(data),
                    sample_rate_hz=self.sample_rate_hz,
                    channels=self.channels,
                    duration_ms=self.frame_duration_ms,
                )
```

- [ ] **Step 4: Add microphone probe CLI**

Append to `endpoint/src/wake_word_endpoint/cli.py`:

```python

@app.command()
def mic_probe(config: Path, frames: int = 50) -> None:
    """Capture a short microphone sample and print frame statistics."""
    from wake_word_endpoint.audio import MicrophoneAudioSource

    loaded = load_config(config)
    source = MicrophoneAudioSource(
        device=loaded.microphone.device,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )
    captured = list(source.frames(max_frames=frames))
    total_bytes = sum(len(frame.pcm) for frame in captured)
    print(
        {
            "frames": len(captured),
            "total_bytes": total_bytes,
            "sample_rate_hz": loaded.microphone.sample_rate_hz,
            "channels": loaded.microphone.channels,
        }
    )
```

- [ ] **Step 5: Run audio tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_audio.py -q
```

Expected:

```text
2 tests pass
```

- [ ] **Step 6: Manually probe microphone on Mac**

Run with the USB mic attached:

```bash
. .venv/bin/activate
wake-endpoint mic-probe endpoint/configs/mac.example.yaml --frames 50
```

Expected:

```text
prints 50 frames and 32000 total bytes for 20 ms, 16 kHz, mono PCM
```

- [ ] **Step 7: Commit**

```bash
git add endpoint/src/wake_word_endpoint/audio.py endpoint/src/wake_word_endpoint/cli.py endpoint/tests/test_audio.py
git commit -m "feat: add endpoint audio capture"
```

## Task 5: Wake-Word Engine Interface And Fake Engine

**Files:**
- Create: `endpoint/src/wake_word_endpoint/wake_engines/__init__.py`
- Create: `endpoint/src/wake_word_endpoint/wake_engines/base.py`
- Create: `endpoint/src/wake_word_endpoint/wake_engines/fake.py`
- Create: `endpoint/tests/test_wake_engines.py`

- [ ] **Step 1: Write failing wake engine tests**

Create `endpoint/tests/test_wake_engines.py`:

```python
from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine


def test_fake_wake_engine_triggers_after_configured_frame_count():
    engine = FakeWakeEngine(trigger_after_frames=3)
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=20)

    assert engine.process(frame) is None
    assert engine.process(frame) is None
    event = engine.process(frame)

    assert event is not None
    assert event.engine == "fake"
    assert event.phrase_track == "builtin-baseline"
    assert event.confidence == 1.0
```

- [ ] **Step 2: Run wake engine test and verify failure**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_wake_engines.py -q
```

Expected:

```text
FAIL with ImportError for wake_word_endpoint.wake_engines.fake
```

- [ ] **Step 3: Implement wake engine interface and fake engine**

Create `endpoint/src/wake_word_endpoint/wake_engines/__init__.py`:

```python
from wake_word_endpoint.wake_engines.base import WakeDetection, WakeEngine
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine

__all__ = ["FakeWakeEngine", "WakeDetection", "WakeEngine"]
```

Create `endpoint/src/wake_word_endpoint/wake_engines/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from wake_word_endpoint.audio import AudioFrame


@dataclass(frozen=True)
class WakeDetection:
    engine: str
    phrase_track: str
    confidence: float
    frame_index: int


class WakeEngine(Protocol):
    name: str
    phrase_track: str

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        """Return a detection event when the wake phrase is detected."""
```

Create `endpoint/src/wake_word_endpoint/wake_engines/fake.py`:

```python
from __future__ import annotations

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class FakeWakeEngine:
    name = "fake"
    phrase_track = "builtin-baseline"

    def __init__(self, trigger_after_frames: int = 10) -> None:
        self.trigger_after_frames = trigger_after_frames
        self._frames_seen = 0
        self._triggered = False

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        self._frames_seen += 1
        if self._triggered or self._frames_seen < self.trigger_after_frames:
            return None
        self._triggered = True
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )
```

- [ ] **Step 4: Run wake engine tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_wake_engines.py -q
```

Expected:

```text
1 test passes
```

- [ ] **Step 5: Commit**

```bash
git add endpoint/src/wake_word_endpoint/wake_engines endpoint/tests/test_wake_engines.py
git commit -m "feat: add wake engine interface"
```

## Task 6: Gateway Client

**Files:**
- Create: `endpoint/src/wake_word_endpoint/gateway_client.py`
- Create: `endpoint/tests/test_gateway_client.py`

- [ ] **Step 1: Write failing gateway client tests**

Create `endpoint/tests/test_gateway_client.py`:

```python
from wake_word_endpoint.gateway_client import GatewayHeaders


def test_gateway_headers_include_endpoint_id_and_bearer_token():
    headers = GatewayHeaders(endpoint_id="mac-studio-01", token="dev-token").to_headers()

    assert headers["Authorization"] == "Bearer dev-token"
    assert headers["X-Endpoint-Id"] == "mac-studio-01"
```

- [ ] **Step 2: Run gateway client test and verify failure**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_gateway_client.py -q
```

Expected:

```text
FAIL with ImportError for wake_word_endpoint.gateway_client
```

- [ ] **Step 3: Implement gateway client**

Create `endpoint/src/wake_word_endpoint/gateway_client.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import websockets

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.protocol import ClientStop, ServerMessage, SessionHello, parse_server_message


@dataclass(frozen=True)
class GatewayHeaders:
    endpoint_id: str
    token: str

    def to_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Endpoint-Id": self.endpoint_id,
        }


class GatewayClient:
    def __init__(self, url: str, endpoint_id: str, token: str) -> None:
        self.url = url
        self.endpoint_id = endpoint_id
        self.token = token

    async def stream_session(
        self,
        hello: SessionHello,
        frames: AsyncIterator[AudioFrame],
        stop_reason: str = "manual",
    ) -> list[ServerMessage]:
        events: list[ServerMessage] = []
        headers = GatewayHeaders(endpoint_id=self.endpoint_id, token=self.token).to_headers()
        async with websockets.connect(self.url, additional_headers=headers) as websocket:
            await websocket.send(hello.to_json())
            accepted_raw = await websocket.recv()
            if not isinstance(accepted_raw, str):
                raise RuntimeError("gateway accepted response must be JSON text")
            accepted = parse_server_message(accepted_raw)
            events.append(accepted)
            async for frame in frames:
                await websocket.send(frame.pcm)
            await websocket.send(ClientStop(reason=stop_reason).to_json())
            while True:
                raw = await websocket.recv()
                if not isinstance(raw, str):
                    raise RuntimeError("gateway event must be JSON text")
                event = parse_server_message(raw)
                events.append(event)
                if event.type in {"session.ended", "error"}:
                    break
        return events
```

- [ ] **Step 4: Run gateway client tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_gateway_client.py -q
```

Expected:

```text
1 test passes
```

- [ ] **Step 5: Commit**

```bash
git add endpoint/src/wake_word_endpoint/gateway_client.py endpoint/tests/test_gateway_client.py
git commit -m "feat: add endpoint gateway client"
```

## Task 7: Endpoint Session Controller

**Files:**
- Create: `endpoint/src/wake_word_endpoint/controller.py`
- Create: `endpoint/tests/test_controller.py`
- Modify: `endpoint/src/wake_word_endpoint/cli.py`

- [ ] **Step 1: Write failing controller test**

Create `endpoint/tests/test_controller.py`:

```python
import asyncio

from wake_word_endpoint.audio import GeneratedAudioSource
from wake_word_endpoint.controller import EndpointController
from wake_word_endpoint.wake_engines.fake import FakeWakeEngine


class RecordingGateway:
    def __init__(self) -> None:
        self.streamed_frames = 0

    async def stream_session(self, hello, frames, stop_reason="manual"):
        async for _frame in frames:
            self.streamed_frames += 1
        return []


def test_controller_streams_only_after_wake_detection():
    source = GeneratedAudioSource(sample_rate_hz=16000, channels=1, frame_duration_ms=20)
    engine = FakeWakeEngine(trigger_after_frames=3)
    gateway = RecordingGateway()
    controller = EndpointController(
        endpoint_id="mac-studio-01",
        endpoint_type="mac-studio",
        run_id="run-001",
        audio_source=source,
        wake_engine=engine,
        gateway_client=gateway,
        sample_rate_hz=16000,
        channels=1,
        frame_duration_ms=20,
        max_stream_frames=5,
    )

    asyncio.run(controller.run_once(max_listen_frames=20))

    assert gateway.streamed_frames == 5
```

- [ ] **Step 2: Run controller test and verify failure**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_controller.py -q
```

Expected:

```text
FAIL with ImportError for wake_word_endpoint.controller
```

- [ ] **Step 3: Implement controller**

Create `endpoint/src/wake_word_endpoint/controller.py`:

```python
from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from typing import Any

from wake_word_endpoint.audio import AudioFrame, AudioSource
from wake_word_endpoint.protocol import AudioSpec, SessionHello, WakeSpec
from wake_word_endpoint.wake_engines.base import WakeEngine


async def _async_frames(frames: list[AudioFrame]) -> AsyncIterator[AudioFrame]:
    for frame in frames:
        yield frame


class EndpointController:
    def __init__(
        self,
        endpoint_id: str,
        endpoint_type: str,
        run_id: str,
        audio_source: AudioSource,
        wake_engine: WakeEngine,
        gateway_client: Any,
        sample_rate_hz: int,
        channels: int,
        frame_duration_ms: int,
        max_stream_frames: int,
    ) -> None:
        self.endpoint_id = endpoint_id
        self.endpoint_type = endpoint_type
        self.run_id = run_id
        self.audio_source = audio_source
        self.wake_engine = wake_engine
        self.gateway_client = gateway_client
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self.frame_duration_ms = frame_duration_ms
        self.max_stream_frames = max_stream_frames

    async def run_once(self, max_listen_frames: int | None = None) -> None:
        source_iter = self.audio_source.frames(max_frames=max_listen_frames)
        for frame in source_iter:
            detection = self.wake_engine.process(frame)
            if detection is None:
                continue

            post_trigger_frames: list[AudioFrame] = []
            for _, stream_frame in zip(range(self.max_stream_frames), source_iter, strict=False):
                post_trigger_frames.append(stream_frame)

            hello = SessionHello(
                endpoint_id=self.endpoint_id,
                endpoint_type=self.endpoint_type,
                run_id=self.run_id,
                audio=AudioSpec(
                    sample_rate_hz=self.sample_rate_hz,
                    channels=self.channels,
                    frame_duration_ms=self.frame_duration_ms,
                ),
                wake=WakeSpec(engine=detection.engine, phrase_track=detection.phrase_track),
                started_at=dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
            )
            await self.gateway_client.stream_session(hello, _async_frames(post_trigger_frames))
            return
```

- [ ] **Step 4: Add run-fake CLI**

Append to `endpoint/src/wake_word_endpoint/cli.py`:

```python

@app.command()
def run_fake(config: Path, token: str = "dev-token", run_id: str = "manual-run") -> None:
    """Run the endpoint with generated audio and a fake wake event."""
    import asyncio

    from wake_word_endpoint.audio import GeneratedAudioSource
    from wake_word_endpoint.controller import EndpointController
    from wake_word_endpoint.gateway_client import GatewayClient
    from wake_word_endpoint.wake_engines.fake import FakeWakeEngine

    loaded = load_config(config)
    source = GeneratedAudioSource(
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )
    gateway = GatewayClient(
        url=loaded.gateway.url,
        endpoint_id=loaded.endpoint.id,
        token=token,
    )
    controller = EndpointController(
        endpoint_id=loaded.endpoint.id,
        endpoint_type=loaded.endpoint.type,
        run_id=run_id,
        audio_source=source,
        wake_engine=FakeWakeEngine(trigger_after_frames=10),
        gateway_client=gateway,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
        max_stream_frames=100,
    )
    asyncio.run(controller.run_once(max_listen_frames=200))
```

- [ ] **Step 5: Run controller tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_controller.py -q
```

Expected:

```text
1 test passes
```

- [ ] **Step 6: Commit**

```bash
git add endpoint/src/wake_word_endpoint/controller.py endpoint/src/wake_word_endpoint/cli.py endpoint/tests/test_controller.py
git commit -m "feat: add endpoint session controller"
```

## Task 8: Gateway Auth, Mock Transcription, And Websocket Server

**Files:**
- Create: `gateway/src/auth.ts`
- Create: `gateway/src/transcription/types.ts`
- Create: `gateway/src/transcription/mock.ts`
- Create: `gateway/src/server.ts`
- Create: `gateway/test/auth.test.ts`
- Create: `gateway/test/server.test.ts`

- [ ] **Step 1: Write gateway auth tests**

Create `gateway/test/auth.test.ts`:

```ts
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
```

- [ ] **Step 2: Implement gateway auth**

Create `gateway/src/auth.ts`:

```ts
export type AuthInput = {
  authorization: string | undefined;
  endpointId: string | undefined;
  expectedToken: string;
};

export type AuthResult = { ok: true; endpointId: string } | { ok: false; reason: string };

export function authenticate(input: AuthInput): AuthResult {
  if (!input.endpointId) {
    return { ok: false, reason: "missing endpoint id" };
  }
  if (!input.authorization?.startsWith("Bearer ")) {
    return { ok: false, reason: "missing bearer token" };
  }
  const token = input.authorization.slice("Bearer ".length);
  if (token !== input.expectedToken) {
    return { ok: false, reason: "invalid bearer token" };
  }
  return { ok: true, endpointId: input.endpointId };
}
```

- [ ] **Step 3: Write gateway server test**

Create `gateway/test/server.test.ts`:

```ts
import { once } from "node:events";
import { AddressInfo } from "node:net";
import { describe, expect, it } from "vitest";
import WebSocket from "ws";
import { buildServer } from "../src/server.js";

describe("gateway server", () => {
  it("accepts hello, binary audio, stop, and returns transcript events", async () => {
    const app = buildServer({ deviceToken: "dev-token", transcriptionMode: "mock" });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });

    await once(ws, "open");
    ws.send(
      JSON.stringify({
        type: "hello",
        protocolVersion: "wake-word.v1",
        endpointId: "mac-studio-01",
        endpointType: "mac-studio",
        runId: "run-001",
        audio: {
          format: "pcm_s16le",
          sampleRateHz: 16000,
          channels: 1,
          frameDurationMs: 20
        },
        wake: {
          engine: "fake",
          phraseTrack: "builtin-baseline"
        },
        startedAt: "2026-05-11T18:00:00Z"
      })
    );
    const accepted = JSON.parse((await once(ws, "message"))[0].toString());
    ws.send(Buffer.alloc(640));
    ws.send(JSON.stringify({ type: "stop", reason: "manual" }));
    const transcript = JSON.parse((await once(ws, "message"))[0].toString());
    const ended = JSON.parse((await once(ws, "message"))[0].toString());

    expect(accepted.type).toBe("session.accepted");
    expect(transcript.type).toBe("transcript.final");
    expect(ended.type).toBe("session.ended");

    ws.close();
    await app.close();
  });
});
```

- [ ] **Step 4: Implement transcription adapter types and mock**

Create `gateway/src/transcription/types.ts`:

```ts
import { TranscriptEvent } from "../protocol.js";

export type TranscriptionAdapter = {
  start(sessionId: string, onEvent: (event: TranscriptEvent) => void): Promise<TranscriptionSession>;
};

export type TranscriptionSession = {
  pushAudio(chunk: Buffer): void;
  stop(): Promise<void>;
};
```

Create `gateway/src/transcription/mock.ts`:

```ts
import { TranscriptEvent, transcriptFinal } from "../protocol.js";
import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

export class MockTranscriptionAdapter implements TranscriptionAdapter {
  async start(sessionId: string, onEvent: (event: TranscriptEvent) => void) {
    let bytes = 0;
    return {
      pushAudio(chunk: Buffer) {
        bytes += chunk.length;
      },
      async stop() {
        onEvent(transcriptFinal(sessionId, `mock transcript from ${bytes} bytes`, 0));
      }
    } satisfies TranscriptionSession;
  }
}
```

- [ ] **Step 5: Implement websocket server**

Create `gateway/src/server.ts`:

```ts
import websocket from "@fastify/websocket";
import Fastify from "fastify";
import { nanoid } from "nanoid";
import { authenticate } from "./auth.js";
import { errorMessage, parseHelloMessage, sessionAccepted } from "./protocol.js";
import { AzureSpeechAdapter } from "./transcription/azureSpeech.js";
import { MockTranscriptionAdapter } from "./transcription/mock.js";
import { TranscriptionAdapter } from "./transcription/types.js";

export type ServerOptions = {
  deviceToken: string;
  transcriptionMode: "mock" | "azure";
};

function buildTranscriptionAdapter(mode: "mock" | "azure"): TranscriptionAdapter {
  if (mode === "azure") {
    return new AzureSpeechAdapter({
      key: process.env.AZURE_SPEECH_KEY ?? "",
      region: process.env.AZURE_SPEECH_REGION ?? ""
    });
  }
  return new MockTranscriptionAdapter();
}

export function buildServer(options: ServerOptions) {
  const app = Fastify({ logger: true });
  const transcription = buildTranscriptionAdapter(options.transcriptionMode);

  app.register(websocket);

  app.get("/healthz", async () => ({ ok: true }));

  app.get("/v1/audio", { websocket: true }, (socket, request) => {
    const auth = authenticate({
      authorization: request.headers.authorization,
      endpointId: request.headers["x-endpoint-id"]?.toString(),
      expectedToken: options.deviceToken
    });

    if (!auth.ok) {
      socket.send(JSON.stringify(errorMessage(auth.reason)));
      socket.close();
      return;
    }

    let accepted = false;
    let session:
      | Awaited<ReturnType<TranscriptionAdapter["start"]>>
      | undefined;
    const sessionId = nanoid();

    socket.on("message", async (raw) => {
      try {
        if (!accepted) {
          const text = raw.toString();
          const hello = parseHelloMessage(JSON.parse(text));
          if (hello.endpointId !== auth.endpointId) {
            throw new Error("endpoint id mismatch");
          }
          session = await transcription.start(sessionId, (event) => {
            socket.send(JSON.stringify(event));
          });
          accepted = true;
          socket.send(JSON.stringify(sessionAccepted(sessionId)));
          return;
        }

        if (Buffer.isBuffer(raw)) {
          session?.pushAudio(raw);
          return;
        }

        const message = JSON.parse(raw.toString());
        if (message.type === "stop") {
          await session?.stop();
          socket.send(JSON.stringify({ type: "session.ended", sessionId, reason: message.reason }));
          socket.close();
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "unknown gateway error";
        socket.send(JSON.stringify(errorMessage(message)));
        socket.close();
      }
    });
  });

  return app;
}
```

- [ ] **Step 6: Add Azure adapter shell used by server imports**

Create `gateway/src/transcription/azureSpeech.ts`:

```ts
import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

export class AzureSpeechAdapter implements TranscriptionAdapter {
  constructor(private readonly options: { key: string; region: string }) {}

  async start(): Promise<TranscriptionSession> {
    if (!this.options.key || !this.options.region) {
      throw new Error("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required in azure mode");
    }
    throw new Error("Azure transcription mode is unavailable in the mock gateway checkpoint");
  }
}
```

- [ ] **Step 7: Run gateway tests**

Run:

```bash
cd gateway
npm test
```

Expected:

```text
auth, protocol, and server tests pass with TRANSCRIPTION_MODE=mock
```

- [ ] **Step 8: Commit**

```bash
git add gateway/src gateway/test
git commit -m "feat: add gateway websocket mock"
```

## Task 9: Local Endpoint-To-Gateway Integration

**Files:**
- Modify: `endpoint/src/wake_word_endpoint/protocol.py`
- Modify: `endpoint/src/wake_word_endpoint/cli.py`
- Modify: `endpoint/tests/test_gateway_client.py`
- Modify: `README.md`

- [ ] **Step 1: Add parsing support for session accepted and ended**

Update `endpoint/tests/test_gateway_client.py`:

```python
from wake_word_endpoint.gateway_client import GatewayHeaders
from wake_word_endpoint.protocol import parse_server_message


def test_gateway_headers_include_endpoint_id_and_bearer_token():
    headers = GatewayHeaders(endpoint_id="mac-studio-01", token="dev-token").to_headers()

    assert headers["Authorization"] == "Bearer dev-token"
    assert headers["X-Endpoint-Id"] == "mac-studio-01"


def test_parse_session_lifecycle_events():
    accepted = parse_server_message(
        '{"type":"session.accepted","sessionId":"abc","maxSessionSeconds":60}'
    )
    ended = parse_server_message('{"type":"session.ended","sessionId":"abc","reason":"manual"}')

    assert accepted.type == "session.accepted"
    assert accepted.session_id == "abc"
    assert ended.type == "session.ended"
    assert ended.reason == "manual"
```

Do not change `protocol.py` in this step. The existing `parse_server_message` implementation maps `sessionId` and `reason`, and this test locks that behavior before the integration smoke test.

- [ ] **Step 2: Run gateway locally**

In one terminal:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token TRANSCRIPTION_MODE=mock npm run dev
```

Expected:

```text
wake-word gateway listening on 0.0.0.0:8080
```

- [ ] **Step 3: Run fake endpoint against local gateway**

In a second terminal:

```bash
. .venv/bin/activate
wake-endpoint run-fake endpoint/configs/mac.example.yaml --token dev-token --run-id local-fake-001
```

Expected gateway log:

```text
accepted websocket connection
session accepted
session ended
```

Expected endpoint behavior:

```text
Process exits without streaming before fake wake trigger
```

- [ ] **Step 4: Print gateway events from endpoint CLI**

Modify the end of `run_fake` in `endpoint/src/wake_word_endpoint/cli.py` so it prints returned events:

```python
    events = asyncio.run(controller.run_once(max_listen_frames=200))
    for event in events or []:
        print(event)
```

Modify `EndpointController.run_once` in `endpoint/src/wake_word_endpoint/controller.py` to return gateway events:

```python
            return await self.gateway_client.stream_session(hello, _async_frames(post_trigger_frames))
        return []
```

- [ ] **Step 5: Re-run local integration**

Run:

```bash
. .venv/bin/activate
wake-endpoint run-fake endpoint/configs/mac.example.yaml --token dev-token --run-id local-fake-002
```

Expected endpoint output includes:

```text
ServerMessage(type='session.accepted'
ServerMessage(type='transcript.final'
ServerMessage(type='session.ended'
```

- [ ] **Step 6: Document local integration quickstart**

Append to `README.md`:

```markdown
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
```

- [ ] **Step 7: Run tests**

Run:

```bash
. .venv/bin/activate
pytest -q
cd gateway
npm test
```

Expected:

```text
All Python and gateway tests pass
```

- [ ] **Step 8: Commit**

```bash
git add README.md endpoint/src/wake_word_endpoint endpoint/tests
git commit -m "feat: connect endpoint to local gateway"
```

## Task 10: Azure Speech Transcription Adapter

**Files:**
- Modify: `gateway/src/transcription/azureSpeech.ts`
- Create: `gateway/test/azureSpeech.test.ts`
- Modify: `docs/azure-gateway.md`

- [ ] **Step 1: Write Azure Speech config test**

Create `gateway/test/azureSpeech.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { AzureSpeechAdapter } from "../src/transcription/azureSpeech.js";

describe("AzureSpeechAdapter", () => {
  it("rejects missing Azure credentials", async () => {
    const adapter = new AzureSpeechAdapter({ key: "", region: "" });

    await expect(adapter.start("session-001", () => undefined)).rejects.toThrow(
      "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required"
    );
  });
});
```

- [ ] **Step 2: Implement Azure Speech adapter**

Replace `gateway/src/transcription/azureSpeech.ts` with:

```ts
import * as sdk from "microsoft-cognitiveservices-speech-sdk";
import { transcriptFinal, transcriptPartial } from "../protocol.js";
import { TranscriptionAdapter, TranscriptionSession } from "./types.js";

export class AzureSpeechAdapter implements TranscriptionAdapter {
  constructor(private readonly options: { key: string; region: string }) {}

  async start(
    sessionId: string,
    onEvent: (event: ReturnType<typeof transcriptPartial> | ReturnType<typeof transcriptFinal>) => void
  ): Promise<TranscriptionSession> {
    if (!this.options.key || !this.options.region) {
      throw new Error("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION are required");
    }

    const speechConfig = sdk.SpeechConfig.fromSubscription(this.options.key, this.options.region);
    speechConfig.speechRecognitionLanguage = "en-US";

    const audioFormat = sdk.AudioStreamFormat.getWaveFormatPCM(16000, 16, 1);
    const pushStream = sdk.AudioInputStream.createPushStream(audioFormat);
    const audioConfig = sdk.AudioConfig.fromStreamInput(pushStream);
    const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

    recognizer.recognizing = (_sender, event) => {
      const text = event.result.text;
      if (text) {
        onEvent(transcriptPartial(sessionId, text, Number(event.result.offset) / 10000));
      }
    };

    recognizer.recognized = (_sender, event) => {
      const text = event.result.text;
      if (text) {
        onEvent(transcriptFinal(sessionId, text, Number(event.result.offset) / 10000));
      }
    };

    await new Promise<void>((resolve, reject) => {
      recognizer.startContinuousRecognitionAsync(resolve, reject);
    });

    return {
      pushAudio(chunk: Buffer) {
        pushStream.write(chunk);
      },
      async stop() {
        pushStream.close();
        await new Promise<void>((resolve, reject) => {
          recognizer.stopContinuousRecognitionAsync(resolve, reject);
        });
        recognizer.close();
      }
    };
  }
}
```

- [ ] **Step 3: Run Azure adapter tests**

Run:

```bash
cd gateway
npm test -- azureSpeech.test.ts
npm run typecheck
```

Expected:

```text
Azure credential validation test passes
TypeScript typecheck passes
```

- [ ] **Step 4: Document Azure Speech environment**

Append to `docs/azure-gateway.md`:

```markdown
## Azure Speech Environment

The gateway uses these environment variables in Azure transcription mode:

```text
TRANSCRIPTION_MODE=azure
AZURE_SPEECH_KEY is read from the Container App secret named azure-speech-key
AZURE_SPEECH_REGION is set to the Azure Speech resource region, for example eastus
GATEWAY_DEVICE_TOKEN is read from the Container App secret named gateway-device-token
```

Endpoints receive only `GATEWAY_DEVICE_TOKEN` or a device-specific gateway credential. They do not receive `AZURE_SPEECH_KEY`.
```

- [ ] **Step 5: Run all gateway tests**

Run:

```bash
cd gateway
npm test
npm run typecheck
```

Expected:

```text
All gateway tests pass
TypeScript typecheck passes
```

- [ ] **Step 6: Commit**

```bash
git add gateway/src/transcription/azureSpeech.ts gateway/test/azureSpeech.test.ts docs/azure-gateway.md
git commit -m "feat: add Azure Speech transcription adapter"
```

## Task 11: Gateway Container And Azure Container Apps Deployment

**Files:**
- Create: `gateway/Dockerfile`
- Create: `infra/README.md`
- Create: `infra/container-app.bicep`
- Modify: `docs/azure-gateway.md`

- [ ] **Step 1: Add Dockerfile**

Create `gateway/Dockerfile`:

```dockerfile
FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM deps AS build
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:20-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
EXPOSE 8080
CMD ["node", "dist/index.js"]
```

- [ ] **Step 2: Build gateway container locally**

Run:

```bash
cd gateway
npm install
docker build -t wake-word-gateway:local .
```

Expected:

```text
Docker image wake-word-gateway:local builds successfully
```

- [ ] **Step 3: Add Azure Container Apps Bicep**

Create `infra/container-app.bicep`:

```bicep
param location string = resourceGroup().location
param containerAppName string = 'wake-word-gateway'
param managedEnvironmentName string = 'wake-word-env'
param image string
param registryServer string
param registryUsername string
@secure()
param registryPassword string
@secure()
param gatewayDeviceToken string
@secure()
param azureSpeechKey string
param azureSpeechRegion string

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: managedEnvironmentName
  location: location
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
      secrets: [
        {
          name: 'gateway-device-token'
          value: gatewayDeviceToken
        }
        {
          name: 'azure-speech-key'
          value: azureSpeechKey
        }
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: image
          env: [
            {
              name: 'PORT'
              value: '8080'
            }
            {
              name: 'TRANSCRIPTION_MODE'
              value: 'azure'
            }
            {
              name: 'GATEWAY_DEVICE_TOKEN'
              secretRef: 'gateway-device-token'
            }
            {
              name: 'AZURE_SPEECH_KEY'
              secretRef: 'azure-speech-key'
            }
            {
              name: 'AZURE_SPEECH_REGION'
              value: azureSpeechRegion
            }
          ]
          resources: {
            cpu: 0.5
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output gatewayUrl string = 'https://${app.properties.configuration.ingress.fqdn}/v1/audio'
```

- [ ] **Step 4: Add deployment docs**

Create `infra/README.md`:

```markdown
# Azure Deployment

The first deployment target is Azure Container Apps.

## Required local tools

- Azure CLI
- Docker
- Node 20

## Build and push image

Create an Azure Container Registry or use an existing registry. Build and push the gateway image:

```bash
cd gateway
npm install
docker build -t wake-word-gateway:local .
```

Tag the image for the registry you choose:

```bash
docker tag wake-word-gateway:local "$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest"
docker push "$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest"
```

## Deploy Container App

```bash
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file infra/container-app.bicep \
  --parameters \
    image="$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest" \
    registryServer="$AZURE_CONTAINER_REGISTRY.azurecr.io" \
    registryUsername="$AZURE_CONTAINER_REGISTRY_USERNAME" \
    registryPassword="$AZURE_CONTAINER_REGISTRY_PASSWORD" \
    gatewayDeviceToken="$GATEWAY_DEVICE_TOKEN" \
    azureSpeechKey="$AZURE_SPEECH_KEY" \
    azureSpeechRegion="$AZURE_SPEECH_REGION"
```

The deployment output contains the websocket URL for endpoint config:

```text
Use the gatewayUrl output from the deployment command as the endpoint gateway URL.
```
```

Append to `docs/azure-gateway.md`:

```markdown
## Hosting Target

The first hosting target is Azure Container Apps. The gateway exposes `/healthz` and `/v1/audio`; `/v1/audio` is a websocket endpoint for post-trigger audio sessions.
```

- [ ] **Step 5: Validate Bicep and container build**

Run:

```bash
az bicep build --file infra/container-app.bicep
cd gateway
docker build -t wake-word-gateway:local .
```

Expected:

```text
Bicep builds successfully
Docker image builds successfully
```

- [ ] **Step 6: Commit**

```bash
git add gateway/Dockerfile infra docs/azure-gateway.md
git commit -m "feat: add Azure gateway deployment"
```

## Task 12: Raspberry Pi 5 Bring-Up

**Files:**
- Create: `scripts/pi/check_audio.sh`
- Modify: `docs/hardware.md`
- Modify: `endpoint/README.md`

- [ ] **Step 1: Add Pi audio check script**

Create `scripts/pi/check_audio.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-/tmp/wake-word-pi-mic-test.wav}"

echo "USB devices:"
lsusb

echo
echo "ALSA capture devices:"
arecord -l

echo
echo "Recording 5 seconds of 16 kHz mono PCM to $OUT"
arecord -f S16_LE -r 16000 -c 1 -d 5 "$OUT"

echo
echo "Audio file details:"
soxi "$OUT"
```

Run:

```bash
chmod +x scripts/pi/check_audio.sh
```

- [ ] **Step 2: Expand hardware docs**

Replace `docs/hardware.md` with:

```markdown
# Hardware

The first comparison uses one USB microphone sequentially:

1. Plug the microphone into the Mac Studio and run a live trial.
2. Move the same microphone to the Raspberry Pi 5 and run the same trial.

This keeps microphone hardware constant without requiring simultaneous capture.

## Raspberry Pi 5 Fresh Setup

Use Raspberry Pi OS Lite 64-bit. Configure hostname, user, SSH, timezone, and network in Raspberry Pi Imager before first boot. Recommended hostname: `wakepi-01`.

Prefer Ethernet for initial testing.

After first SSH login:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git python3-full python3-venv python3-pip build-essential pkg-config alsa-utils portaudio19-dev ffmpeg sox
```

Validate the USB microphone:

```bash
scripts/pi/check_audio.sh
```

Expected result:

```text
arecord creates a 5 second WAV file
soxi reports 16000 Hz, 1 channel, 16-bit PCM
```

## Project Python Environment On Pi

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Use a virtual environment because Raspberry Pi OS protects the system Python environment.
```

- [ ] **Step 3: Update endpoint README with Pi flow**

Append to `endpoint/README.md`:

```markdown
## Raspberry Pi 5 Bring-Up

1. Flash Raspberry Pi OS Lite 64-bit.
2. Enable SSH and set hostname `wakepi-01`.
3. Install audio and Python dependencies from `docs/hardware.md`.
4. Run `scripts/pi/check_audio.sh`.
5. Create a Python virtual environment and install this repo.
6. Run `wake-endpoint config-check endpoint/configs/pi.example.yaml`.
7. Run `wake-endpoint mic-probe endpoint/configs/pi.example.yaml --frames 50`.
```

- [ ] **Step 4: Run shellcheck-compatible syntax check**

Run:

```bash
bash -n scripts/pi/check_audio.sh
```

Expected:

```text
No output and exit code 0
```

- [ ] **Step 5: Commit**

```bash
git add scripts/pi/check_audio.sh docs/hardware.md endpoint/README.md
git commit -m "docs: add Raspberry Pi bring-up"
```

## Task 13: OpenWakeWord Adapter

**Files:**
- Create: `endpoint/src/wake_word_endpoint/wake_engines/openwakeword.py`
- Modify: `endpoint/tests/test_wake_engines.py`
- Modify: `docs/wake-word-evaluation.md`

- [ ] **Step 1: Add OpenWakeWord adapter tests with a fake model**

Append to `endpoint/tests/test_wake_engines.py`:

```python
from wake_word_endpoint.wake_engines.openwakeword import OpenWakeWordEngine


class FakeOpenWakeWordModel:
    def __init__(self) -> None:
        self.calls = 0

    def predict(self, pcm):
        self.calls += 1
        return {"hey_assistant": 0.9 if self.calls == 2 else 0.1}


def test_openwakeword_adapter_triggers_above_threshold():
    engine = OpenWakeWordEngine(
        model=FakeOpenWakeWordModel(),
        model_name="hey_assistant",
        phrase_track="builtin-baseline",
        threshold=0.8,
    )
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=80)

    assert engine.process(frame) is None
    event = engine.process(frame)

    assert event is not None
    assert event.engine == "openwakeword"
    assert event.confidence == 0.9
```

- [ ] **Step 2: Implement OpenWakeWord adapter**

Create `endpoint/src/wake_word_endpoint/wake_engines/openwakeword.py`:

```python
from __future__ import annotations

import numpy as np

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class OpenWakeWordEngine:
    name = "openwakeword"

    def __init__(
        self,
        model: object,
        model_name: str,
        phrase_track: str,
        threshold: float = 0.5,
    ) -> None:
        self.model = model
        self.model_name = model_name
        self.phrase_track = phrase_track
        self.threshold = threshold
        self._frames_seen = 0

    @classmethod
    def from_default_model(
        cls,
        model_name: str = "hey_jarvis",
        phrase_track: str = "builtin-baseline",
        threshold: float = 0.5,
    ) -> "OpenWakeWordEngine":
        from openwakeword.model import Model

        return cls(
            model=Model(wakeword_models=[model_name]),
            model_name=model_name,
            phrase_track=phrase_track,
            threshold=threshold,
        )

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        self._frames_seen += 1
        pcm = np.frombuffer(frame.pcm, dtype=np.int16)
        prediction = self.model.predict(pcm)
        confidence = float(prediction.get(self.model_name, 0.0))
        if confidence < self.threshold:
            return None
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=confidence,
            frame_index=self._frames_seen,
        )
```

- [ ] **Step 3: Document OpenWakeWord evaluation notes**

Append to `docs/wake-word-evaluation.md`:

```markdown
## OpenWakeWord Track

OpenWakeWord is the first open-source candidate. Start with a built-in model to evaluate integration, CPU, memory, and false accepts before investing in a surgical-domain phrase.

Install with:

```bash
python -m pip install -e ".[openwakeword]"
```
```

- [ ] **Step 4: Run wake engine tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_wake_engines.py -q
```

Expected:

```text
Fake and OpenWakeWord adapter tests pass without requiring the openwakeword package
```

- [ ] **Step 5: Commit**

```bash
git add endpoint/src/wake_word_endpoint/wake_engines/openwakeword.py endpoint/tests/test_wake_engines.py docs/wake-word-evaluation.md
git commit -m "feat: add OpenWakeWord adapter"
```

## Task 14: Picovoice Porcupine Adapter

**Files:**
- Create: `endpoint/src/wake_word_endpoint/wake_engines/porcupine.py`
- Modify: `endpoint/tests/test_wake_engines.py`
- Modify: `docs/wake-word-evaluation.md`

- [ ] **Step 1: Add Porcupine adapter test with fake engine**

Append to `endpoint/tests/test_wake_engines.py`:

```python
from wake_word_endpoint.wake_engines.porcupine import PorcupineEngine


class FakePorcupine:
    sample_rate = 16000
    frame_length = 512

    def __init__(self) -> None:
        self.calls = 0

    def process(self, pcm):
        self.calls += 1
        return 0 if self.calls == 2 else -1


def test_porcupine_adapter_triggers_on_keyword_index():
    engine = PorcupineEngine(
        porcupine=FakePorcupine(),
        keyword_names=["hey_or_assistant"],
        phrase_track="surgical-domain",
    )
    frame = AudioFrame.pcm_silence(sample_rate_hz=16000, channels=1, duration_ms=32)

    assert engine.process(frame) is None
    event = engine.process(frame)

    assert event is not None
    assert event.engine == "porcupine"
    assert event.phrase_track == "surgical-domain"
    assert event.confidence == 1.0
```

- [ ] **Step 2: Implement Porcupine adapter**

Create `endpoint/src/wake_word_endpoint/wake_engines/porcupine.py`:

```python
from __future__ import annotations

import numpy as np

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.wake_engines.base import WakeDetection


class PorcupineEngine:
    name = "porcupine"

    def __init__(self, porcupine: object, keyword_names: list[str], phrase_track: str) -> None:
        self.porcupine = porcupine
        self.keyword_names = keyword_names
        self.phrase_track = phrase_track
        self._frames_seen = 0

    @classmethod
    def from_keywords(
        cls,
        access_key: str,
        keywords: list[str],
        phrase_track: str = "builtin-baseline",
    ) -> "PorcupineEngine":
        import pvporcupine

        porcupine = pvporcupine.create(access_key=access_key, keywords=keywords)
        return cls(porcupine=porcupine, keyword_names=keywords, phrase_track=phrase_track)

    def process(self, frame: AudioFrame) -> WakeDetection | None:
        self._frames_seen += 1
        pcm = np.frombuffer(frame.pcm, dtype=np.int16)
        keyword_index = int(self.porcupine.process(pcm))
        if keyword_index < 0:
            return None
        return WakeDetection(
            engine=self.name,
            phrase_track=self.phrase_track,
            confidence=1.0,
            frame_index=self._frames_seen,
        )
```

- [ ] **Step 3: Document Porcupine evaluation notes**

Append to `docs/wake-word-evaluation.md`:

```markdown
## Porcupine Track

Porcupine is the first commercial embedded-oriented candidate. Evaluate:

- built-in keyword quality
- custom phrase workflow
- license fit
- Raspberry Pi 5 CPU and memory
- whether access keys and model files can be managed cleanly

Install with:

```bash
python -m pip install -e ".[porcupine]"
```

Provide the access key with an environment variable:

```bash
read -r -s PICOVOICE_ACCESS_KEY
export PICOVOICE_ACCESS_KEY
```
```

- [ ] **Step 4: Run wake engine tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_wake_engines.py -q
```

Expected:

```text
Fake, OpenWakeWord, and Porcupine adapter tests pass without requiring live vendor credentials
```

- [ ] **Step 5: Commit**

```bash
git add endpoint/src/wake_word_endpoint/wake_engines/porcupine.py endpoint/tests/test_wake_engines.py docs/wake-word-evaluation.md
git commit -m "feat: add Porcupine adapter"
```

## Task 15: Live Trial Evaluation Reports

**Files:**
- Create: `eval/src/wake_word_eval/__init__.py`
- Create: `eval/src/wake_word_eval/trial.py`
- Create: `eval/src/wake_word_eval/report.py`
- Create: `eval/tests/test_report.py`
- Create: `eval/live_trial_template.yaml`
- Modify: `docs/wake-word-evaluation.md`

- [ ] **Step 1: Write failing report test**

Create `eval/tests/test_report.py`:

```python
from wake_word_eval.report import summarize_trial
from wake_word_eval.trial import LiveTrial


def test_summarize_trial_marks_live_metrics_observational():
    trial = LiveTrial(
        run_id="mac-openwakeword-001",
        endpoint_type="mac-studio",
        microphone="usb-mic-a",
        wake_engine="openwakeword",
        phrase_track="builtin-baseline",
        false_accepts=0,
        missed_detections=1,
        trigger_to_first_transcript_ms=850,
        notes="quiet office",
    )

    summary = summarize_trial(trial)

    assert summary["run_id"] == "mac-openwakeword-001"
    assert summary["metric_quality"] == "observational-live"
    assert summary["missed_detections"] == 1
```

- [ ] **Step 2: Implement trial model and report summary**

Create `eval/src/wake_word_eval/__init__.py`:

```python
__all__ = []
```

Create `eval/src/wake_word_eval/trial.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiveTrial:
    run_id: str
    endpoint_type: str
    microphone: str
    wake_engine: str
    phrase_track: str
    false_accepts: int
    missed_detections: int
    trigger_to_first_transcript_ms: int | None
    notes: str
```

Create `eval/src/wake_word_eval/report.py`:

```python
from __future__ import annotations

import typer
import yaml

from wake_word_eval.trial import LiveTrial

app = typer.Typer(no_args_is_help=True)


def summarize_trial(trial: LiveTrial) -> dict[str, object]:
    return {
        "run_id": trial.run_id,
        "endpoint_type": trial.endpoint_type,
        "microphone": trial.microphone,
        "wake_engine": trial.wake_engine,
        "phrase_track": trial.phrase_track,
        "metric_quality": "observational-live",
        "false_accepts": trial.false_accepts,
        "missed_detections": trial.missed_detections,
        "trigger_to_first_transcript_ms": trial.trigger_to_first_transcript_ms,
        "notes": trial.notes,
    }


@app.command()
def summarize(path: str) -> None:
    data = yaml.safe_load(open(path, encoding="utf-8"))
    trial = LiveTrial(**data)
    typer.echo(yaml.safe_dump(summarize_trial(trial), sort_keys=False))
```

- [ ] **Step 3: Add live trial template**

Create `eval/live_trial_template.yaml`:

```yaml
run_id: mac-openwakeword-001
endpoint_type: mac-studio
microphone: usb-mic-a
wake_engine: openwakeword
phrase_track: builtin-baseline
false_accepts: 0
missed_detections: 0
trigger_to_first_transcript_ms: null
notes: "quiet office, USB mic approximately 1 meter from speaker"
```

- [ ] **Step 4: Document live-trial protocol**

Append to `docs/wake-word-evaluation.md`:

```markdown
## Live Trial Protocol

For each run:

1. Record endpoint type, microphone, wake engine, phrase track, and room notes.
2. Run idle listening and count false accepts.
3. Speak the wake phrase ten times and count missed detections.
4. Record time from trigger to first transcript when available.
5. Mark results as `observational-live`.

Use `eval/live_trial_template.yaml` as the run record format.
```

- [ ] **Step 5: Run evaluation tests and sample report**

Run:

```bash
. .venv/bin/activate
pytest eval/tests/test_report.py -q
wake-eval-report summarize eval/live_trial_template.yaml
```

Expected:

```text
Evaluation test passes
CLI output includes metric_quality: observational-live
```

- [ ] **Step 6: Commit**

```bash
git add eval docs/wake-word-evaluation.md
git commit -m "feat: add live trial reporting"
```

## Task 16: Review-Driven Hardening

**Files:**
- Modify: `endpoint/src/wake_word_endpoint/gateway_client.py`
- Modify: `endpoint/tests/test_gateway_client.py`
- Modify: `endpoint/src/wake_word_endpoint/controller.py`
- Modify: `endpoint/tests/test_controller.py`
- Modify: `endpoint/src/wake_word_endpoint/cli.py`
- Modify: `gateway/src/server.ts`
- Create: `gateway/src/metrics.ts`
- Create: `gateway/test/metrics.test.ts`
- Modify: `gateway/test/server.test.ts`
- Modify: `docs/azure-gateway.md`
- Modify: `docs/hardware.md`
- Modify: `docs/wake-word-evaluation.md`

- [ ] **Step 1: Add endpoint retry policy tests**

Append to `endpoint/tests/test_gateway_client.py`:

```python
import pytest

from wake_word_endpoint.gateway_client import GatewayConnectionError, GatewayRetryPolicy


def test_retry_policy_uses_bounded_exponential_backoff_without_jitter_for_tests():
    policy = GatewayRetryPolicy(
        max_attempts=4,
        base_delay_seconds=0.25,
        max_delay_seconds=1.0,
        jitter_ratio=0.0,
    )

    assert [policy.delay_for_attempt(attempt) for attempt in range(3)] == [0.25, 0.5, 1.0]


def test_retry_policy_rejects_invalid_attempt_count():
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        GatewayRetryPolicy(max_attempts=0)


def test_gateway_connection_error_names_endpoint_and_attempts():
    error = GatewayConnectionError(endpoint_id="mac-studio-01", attempts=3, reason="refused")

    assert "mac-studio-01" in str(error)
    assert "3 attempts" in str(error)
    assert "refused" in str(error)
```

- [ ] **Step 2: Implement endpoint retry policy and connection error**

Update `endpoint/src/wake_word_endpoint/gateway_client.py`:

```python
from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import websockets

from wake_word_endpoint.audio import AudioFrame
from wake_word_endpoint.protocol import ClientStop, ServerMessage, SessionHello, parse_server_message


@dataclass(frozen=True)
class GatewayHeaders:
    endpoint_id: str
    token: str

    def to_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Endpoint-Id": self.endpoint_id,
        }


@dataclass(frozen=True)
class GatewayRetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 2.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be positive")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be greater than or equal to base_delay_seconds")
        if self.jitter_ratio < 0:
            raise ValueError("jitter_ratio must not be negative")

    def delay_for_attempt(self, attempt: int) -> float:
        base_delay = min(self.max_delay_seconds, self.base_delay_seconds * (2**attempt))
        jitter = 0.0 if self.jitter_ratio == 0 else random.uniform(0.0, base_delay * self.jitter_ratio)
        return base_delay + jitter


class GatewayConnectionError(RuntimeError):
    def __init__(self, endpoint_id: str, attempts: int, reason: str) -> None:
        super().__init__(
            f"gateway connection failed for endpoint {endpoint_id} after {attempts} attempts: {reason}"
        )


class GatewayClient:
    def __init__(
        self,
        url: str,
        endpoint_id: str,
        token: str,
        retry_policy: GatewayRetryPolicy | None = None,
    ) -> None:
        self.url = url
        self.endpoint_id = endpoint_id
        self.token = token
        self.retry_policy = retry_policy or GatewayRetryPolicy()

    async def stream_session(
        self,
        hello: SessionHello,
        frames: AsyncIterator[AudioFrame],
        stop_reason: str = "manual",
    ) -> list[ServerMessage]:
        websocket, events = await self._connect_and_accept(hello)
        try:
            async for frame in frames:
                await websocket.send(frame.pcm)
            await websocket.send(ClientStop(reason=stop_reason).to_json())
            while True:
                raw = await websocket.recv()
                if not isinstance(raw, str):
                    raise RuntimeError("gateway event must be JSON text")
                event = parse_server_message(raw)
                events.append(event)
                if event.type in {"session.ended", "error"}:
                    break
        except (OSError, TimeoutError, websockets.exceptions.WebSocketException) as error:
            raise GatewayConnectionError(
                self.endpoint_id,
                attempts=1,
                reason=f"active stream interrupted: {error}",
            ) from error
        finally:
            await websocket.close()
        return events

    async def _connect_and_accept(self, hello: SessionHello) -> tuple[Any, list[ServerMessage]]:
        last_error: Exception | None = None
        for attempt in range(self.retry_policy.max_attempts):
            try:
                headers = GatewayHeaders(endpoint_id=self.endpoint_id, token=self.token).to_headers()
                websocket = await websockets.connect(self.url, additional_headers=headers)
                await websocket.send(hello.to_json())
                accepted_raw = await websocket.recv()
                if not isinstance(accepted_raw, str):
                    await websocket.close()
                    raise RuntimeError("gateway accepted response must be JSON text")
                accepted = parse_server_message(accepted_raw)
                return websocket, [accepted]
            except (OSError, TimeoutError, websockets.exceptions.WebSocketException) as error:
                last_error = error
                if attempt == self.retry_policy.max_attempts - 1:
                    break
                await asyncio.sleep(self.retry_policy.delay_for_attempt(attempt))
        reason = str(last_error) if last_error else "unknown error"
        raise GatewayConnectionError(self.endpoint_id, self.retry_policy.max_attempts, reason)
```

- [ ] **Step 3: Stream controller frames as they are captured**

Update `_async_frames` and the wake-detection branch in `endpoint/src/wake_word_endpoint/controller.py`:

```python
import asyncio
```

```python
async def _async_frames(
    source_iter,
    max_frames: int,
) -> AsyncIterator[AudioFrame]:
    for _, frame in zip(range(max_frames), source_iter, strict=False):
        yield frame
        await asyncio.sleep(0)
```

```python
            hello = SessionHello(
                endpoint_id=self.endpoint_id,
                endpoint_type=self.endpoint_type,
                run_id=self.run_id,
                audio=AudioSpec(
                    sample_rate_hz=self.sample_rate_hz,
                    channels=self.channels,
                    frame_duration_ms=self.frame_duration_ms,
                ),
                wake=WakeSpec(engine=detection.engine, phrase_track=detection.phrase_track),
                started_at=dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
            )
            return await self.gateway_client.stream_session(
                hello,
                _async_frames(source_iter, self.max_stream_frames),
            )
        return []
```

Keep `endpoint/tests/test_controller.py` asserting `gateway.streamed_frames == 5`. That assertion now proves the controller starts the gateway session after wake detection and streams exactly the next five frames without pre-buffering them into a list.

- [ ] **Step 4: Add gateway metrics tests**

Create `gateway/test/metrics.test.ts`:

```ts
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
```

- [ ] **Step 5: Implement gateway metrics**

Create `gateway/src/metrics.ts`:

```ts
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
```

- [ ] **Step 6: Add gateway negative websocket tests**

Append to `gateway/test/server.test.ts`:

```ts
  it("rejects invalid endpoint tokens", async () => {
    const app = buildServer({ deviceToken: "dev-token", transcriptionMode: "mock" });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer wrong-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });

    await once(ws, "open");
    const error = JSON.parse((await once(ws, "message"))[0].toString());

    expect(error.type).toBe("error");
    expect(error.message).toBe("invalid bearer token");

    ws.close();
    await app.close();
  });

  it("returns an error for malformed hello messages", async () => {
    const app = buildServer({ deviceToken: "dev-token", transcriptionMode: "mock" });
    await app.listen({ port: 0, host: "127.0.0.1" });
    const address = app.server.address() as AddressInfo;
    const ws = new WebSocket(`ws://127.0.0.1:${address.port}/v1/audio`, {
      headers: {
        Authorization: "Bearer dev-token",
        "X-Endpoint-Id": "mac-studio-01"
      }
    });

    await once(ws, "open");
    ws.send(JSON.stringify({ type: "hello", protocolVersion: "wrong" }));
    const error = JSON.parse((await once(ws, "message"))[0].toString());

    expect(error.type).toBe("error");
    expect(error.message).toContain("unsupported protocol version");

    ws.close();
    await app.close();
  });
```

- [ ] **Step 7: Wire metrics into the gateway server**

Modify `gateway/src/server.ts`:

```ts
import websocket from "@fastify/websocket";
import Fastify from "fastify";
import { nanoid } from "nanoid";
import { authenticate } from "./auth.js";
import { GatewayMetrics } from "./metrics.js";
import { errorMessage, parseHelloMessage, sessionAccepted } from "./protocol.js";
import { AzureSpeechAdapter } from "./transcription/azureSpeech.js";
import { MockTranscriptionAdapter } from "./transcription/mock.js";
import { TranscriptionAdapter } from "./transcription/types.js";
```

Add a metrics instance near the transcription adapter:

```ts
  const transcription = buildTranscriptionAdapter(options.transcriptionMode);
  const metrics = new GatewayMetrics();
```

Add the metrics route after `/healthz`:

```ts
  app.get("/metrics", async (_request, reply) => {
    reply.type("text/plain; version=0.0.4");
    return metrics.render();
  });
```

Record auth and session failures:

```ts
    if (!auth.ok) {
      metrics.recordError();
      socket.send(JSON.stringify(errorMessage(auth.reason)));
      socket.close();
      return;
    }
```

Record started, ended, and error counts inside the message handler:

```ts
          session = await transcription.start(sessionId, (event) => {
            socket.send(JSON.stringify(event));
          });
          metrics.recordSessionStarted();
          accepted = true;
          socket.send(JSON.stringify(sessionAccepted(sessionId)));
          return;
```

```ts
        if (message.type === "stop") {
          await session?.stop();
          metrics.recordSessionEnded();
          socket.send(JSON.stringify({ type: "session.ended", sessionId, reason: message.reason }));
          socket.close();
        }
```

```ts
      } catch (error) {
        metrics.recordError();
        const message = error instanceof Error ? error.message : "unknown gateway error";
        socket.send(JSON.stringify(errorMessage(message)));
        socket.close();
      }
```

- [ ] **Step 8: Add Pi audio profiling CLI command**

Append to `endpoint/src/wake_word_endpoint/cli.py`:

```python

@app.command()
def audio_profile(config: Path, frames: int = 200) -> None:
    """Capture microphone frames and print simple timing/buffer profile data."""
    import statistics
    import time

    from wake_word_endpoint.audio import MicrophoneAudioSource

    loaded = load_config(config)
    source = MicrophoneAudioSource(
        device=loaded.microphone.device,
        sample_rate_hz=loaded.microphone.sample_rate_hz,
        channels=loaded.microphone.channels,
        frame_duration_ms=loaded.session.frame_duration_ms,
    )

    timestamps: list[float] = []
    byte_counts: list[int] = []
    for frame in source.frames(max_frames=frames):
        timestamps.append(time.monotonic())
        byte_counts.append(len(frame.pcm))

    intervals_ms = [
        (current - previous) * 1000 for previous, current in zip(timestamps, timestamps[1:])
    ]
    print(
        {
            "frames": len(byte_counts),
            "expected_frame_duration_ms": loaded.session.frame_duration_ms,
            "bytes_per_frame_min": min(byte_counts),
            "bytes_per_frame_max": max(byte_counts),
            "interval_ms_mean": round(statistics.mean(intervals_ms), 2) if intervals_ms else None,
            "interval_ms_max": round(max(intervals_ms), 2) if intervals_ms else None,
        }
    )
```

- [ ] **Step 9: Document Pi/Mac audio profiling and platform differences**

Append to `docs/hardware.md`:

```markdown
## Audio Profiling Before Wake-Word Comparison

Do not assume the Mac Studio and Raspberry Pi 5 expose identical microphone behavior. The Mac uses CoreAudio; the Pi uses Linux audio APIs such as ALSA, and USB timing, default devices, and buffer behavior can differ.

Run this before comparing wake-word engines on each endpoint:

```bash
. .venv/bin/activate
wake-endpoint audio-profile endpoint/configs/mac.example.yaml --frames 200
```

On the Pi:

```bash
. .venv/bin/activate
wake-endpoint audio-profile endpoint/configs/pi.example.yaml --frames 200
```

Record the mean and max inter-frame interval in each live trial. If the Pi shows large timing spikes or capture errors, fix the audio device configuration before attributing poor results to a wake-word engine.
```

- [ ] **Step 10: Document Azure latency posture and metrics**

Append to `docs/azure-gateway.md`:

```markdown
## Latency And Health Checks

The Container Apps deployment keeps `minReplicas: 1` intentionally. This avoids cold-start latency during demos and makes trigger-to-first-transcript measurements more meaningful.

Verify the gateway before live trials:

```bash
curl -fsS "$GATEWAY_BASE_URL/healthz"
curl -fsS "$GATEWAY_BASE_URL/metrics"
```

Record trigger-to-first-transcript latency in live trial reports. Treat latency spikes as gateway/Azure/network findings until endpoint capture timing has also been checked.
```

- [ ] **Step 11: Document deferred evaluation lab work**

Append to `docs/wake-word-evaluation.md`:

```markdown
## Deferred Evaluation Lab

Milestone 1 uses live microphone trials only. That is enough to validate the architecture and catch obvious integration failures, but it is not enough to make strong accuracy claims.

The next evaluation milestone should add:

- recorded positive wake-phrase fixtures
- negative speech samples that should not trigger
- silence and idle-room samples for false accept testing
- controllable noise overlays for SNR curves
- surgical-suite-like noise profiles when legally and practically available
- optional preprocessing experiments, measured against the raw-audio baseline

Do not enable audio preprocessing by default until raw engine behavior has been measured. Preprocessing should be an explicit experiment so it does not hide engine-specific weaknesses.
```

- [ ] **Step 12: Run hardening tests**

Run:

```bash
. .venv/bin/activate
pytest endpoint/tests/test_gateway_client.py endpoint/tests/test_controller.py -q
cd gateway
npm test -- metrics.test.ts server.test.ts
npm run typecheck
```

Expected:

```text
Gateway client retry policy tests pass
Gateway metrics and negative websocket tests pass
Gateway typecheck passes
```

- [ ] **Step 13: Commit**

```bash
git add endpoint/src/wake_word_endpoint/gateway_client.py endpoint/src/wake_word_endpoint/controller.py endpoint/src/wake_word_endpoint/cli.py endpoint/tests/test_gateway_client.py endpoint/tests/test_controller.py gateway/src gateway/test docs
git commit -m "feat: harden gateway streaming path"
```

## Task 17: Final Milestone Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/azure-gateway.md`
- Modify: `docs/hardware.md`
- Modify: `docs/wake-word-evaluation.md`

- [ ] **Step 1: Run full local verification**

Run:

```bash
. .venv/bin/activate
pytest -q
cd gateway
npm test
npm run typecheck
```

Expected:

```text
All Python tests pass
All gateway tests pass
Gateway typecheck passes
```

- [ ] **Step 2: Run local mock gateway smoke test**

Terminal 1:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token TRANSCRIPTION_MODE=mock npm run dev
```

Terminal 2:

```bash
. .venv/bin/activate
wake-endpoint run-fake endpoint/configs/mac.example.yaml --token dev-token --run-id final-local-smoke
```

Expected:

```text
Endpoint prints session.accepted, transcript.final, and session.ended
```

- [ ] **Step 3: Run microphone smoke test on Mac**

With the USB microphone attached to the Mac Studio:

```bash
. .venv/bin/activate
wake-endpoint mic-probe endpoint/configs/mac.example.yaml --frames 50
```

Expected:

```text
50 frames captured
32000 total bytes
```

- [ ] **Step 4: Run Pi audio script syntax verification**

Run:

```bash
bash -n scripts/pi/check_audio.sh
```

Expected:

```text
No output and exit code 0
```

- [ ] **Step 5: Update README with current milestone status**

Append to `README.md`:

```markdown
## Milestone 1 Status

Implemented:

- endpoint/gateway protocol contract
- Python endpoint config, audio source, fake wake engine, gateway client, and controller
- TypeScript gateway websocket server with auth and mock transcription
- Azure Speech adapter and Container Apps deployment files
- Raspberry Pi 5 bring-up docs and audio check script
- OpenWakeWord and Porcupine adapter wrappers
- live-trial observational report format
- gateway retry policy, negative protocol tests, Pi audio profiling, and basic gateway metrics

Verified:

- Python tests
- gateway tests and typecheck
- local fake endpoint to mock gateway smoke test
- Mac microphone probe when USB mic is attached
- gateway `/healthz` and `/metrics` when deployed or running locally
```

- [ ] **Step 6: Commit**

```bash
git add README.md docs
git commit -m "docs: document milestone verification"
```

## Self-Review Checklist

- Spec coverage:
  - Endpoint local wake decision is covered by Tasks 4, 5, 7, 13, and 14.
  - No pre-trigger streaming is covered by Task 7 and the Task 9 smoke test.
  - Gateway-owned Azure credentials are covered by Tasks 8, 10, and 11.
  - Azure-hosted gateway is covered by Task 11.
  - Microsoft transcription is covered by Task 10.
  - Raspberry Pi 5 setup is covered by Task 12.
  - Live-only observational evaluation is covered by Task 15.
  - Multiple wake-word engines are covered by Tasks 13 and 14.
  - External review hardening is covered by Task 16.
  - Recorded fixtures, noise curves, and preprocessing experiments are explicitly deferred outside Milestone 1.
- Type consistency:
  - Python wire keys are camelCase only at the JSON boundary.
  - Python internal dataclasses use snake_case.
  - Gateway protocol uses the same `wake-word.v1` contract as the endpoint.
  - Audio is fixed to 16 kHz, mono, PCM signed 16-bit little-endian for the first milestone.
  - WebSocket remains the Milestone 1 endpoint/gateway transport.
- Verification gates:
  - Every implementation task has test or smoke-test commands.
  - Every task ends with a narrow commit.
