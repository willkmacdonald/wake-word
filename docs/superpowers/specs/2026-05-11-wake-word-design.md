# Wake-Word Exploration Design

Date: 2026-05-11

## Purpose

This repo will explore wake-word approaches for a surgical-suite ambient-listening system. The first demo should validate the end-to-end listening architecture, not clinical summarization or assistant behavior.

The demo target is:

```text
USB microphone
-> local endpoint on Mac Studio or Raspberry Pi 5
-> local wake-word detection
-> post-trigger live audio stream
-> Azure-hosted gateway
-> Microsoft speech/transcription service
-> live transcript
```

The endpoint must not stream audio before local wake-word activation. The first visible output is a live transcript only.

## Primary Design Decisions

- Optimize for a surgical-suite-shaped architecture while testing on available hardware.
- Compare Mac Studio and Raspberry Pi 5 as local endpoints.
- Use the same USB microphone sequentially on each endpoint, moving it between devices for comparison runs.
- Detect wake words locally on the endpoint.
- Stream only post-trigger audio to the gateway.
- Host the gateway in Azure from the start.
- Use Microsoft/Azure speech and AI services by default.
- Keep Azure credentials and policy enforcement in the gateway, not on endpoints.
- Compare multiple wake-word engines from day one so weak candidates can be abandoned quickly.
- Start with live microphone testing only, while labeling early metrics as observational.

## Architecture

The repo should contain three main areas:

```text
endpoint/
  Runs on Mac Studio or Raspberry Pi 5.
  Owns microphone capture, rolling audio buffer, wake-word engine plugins,
  post-trigger streaming, endpoint health, and local logs.

gateway/
  Runs in Azure.
  Authenticates endpoints, accepts post-trigger audio streams, creates sessions,
  forwards audio to Azure Speech or Azure OpenAI Realtime, and returns transcript
  events to the endpoint or demo UI.

eval/
  Supports live test runs, engine comparison reports, endpoint configuration,
  and metric capture.
```

The key boundary is:

```text
Wake-word decision: endpoint
Azure credentials: gateway
Raw post-trigger audio stream: endpoint -> gateway -> Azure
Ambient pre-trigger audio: local only, in memory, not uploaded by default
Transcript output: gateway -> endpoint/UI
```

## Endpoint Responsibilities

The endpoint is the local process connected to the microphone. It should run on both Mac Studio and Raspberry Pi 5 with the same behavior where practical.

Responsibilities:

- Open and monitor the configured microphone.
- Maintain a small local rolling audio buffer in memory.
- Feed microphone audio to one or more wake-word engines through a common interface.
- Start a session when the selected engine detects the wake word.
- Stream post-trigger audio frames to the Azure-hosted gateway.
- Stop the session on silence, timeout, or manual stop.
- Record local run metadata such as endpoint ID, engine name, phrase track, trigger time, CPU, memory, and local errors.

The endpoint should avoid owning cloud credentials or Azure-specific policy. Its cloud-facing responsibility is limited to authenticating with the gateway and streaming session audio after activation.

## Gateway Responsibilities

The gateway is the controlled service boundary between room endpoints and Azure speech/AI services.

Responsibilities:

- Authenticate endpoint connections.
- Authorize endpoint IDs and configuration profiles.
- Terminate endpoint websocket sessions.
- Enforce session policy such as max duration, accepted audio format, and idle timeout.
- Forward post-trigger audio to Microsoft transcription services.
- Return transcript events to the endpoint or demo UI.
- Log metadata needed for debugging and evaluation without storing ambient pre-trigger audio.

The gateway exists because a surgical-suite-shaped deployment needs a central place for credentials, privacy policy, auditability, endpoint management, and future integration boundaries.

## Streaming Model

Before wake-word activation:

```text
Mic -> endpoint -> local wake-word detector
No cloud audio stream
```

After wake-word activation:

```text
Mic -> endpoint -> authenticated websocket -> Azure-hosted gateway -> Azure transcription
Azure transcript events -> gateway -> endpoint/UI
```

The first implementation plan should define exact audio encoding and framing. The design preference is small audio chunks suitable for low-latency transcription, with session metadata sent at stream start.

## Wake-Word Evaluation

Wake-word engines should use a common interface so candidates receive the same microphone stream and emit comparable events.

Initial phrase tracks:

- Built-in phrase baseline: use vendor-provided or built-in phrases first to evaluate integration quality, latency, false accepts, missed detections, and resource usage.
- Surgical-domain phrase: add a custom phrase track after the pipeline works. A representative phrase class is "Hey OR assistant."

Initial candidate engines:

- OpenWakeWord: open-source, Python-friendly, and practical for early Mac/Pi exploration.
- Picovoice Porcupine: strong commercial local wake-word option with embedded support; licensing and custom phrase workflow must be evaluated explicitly.
- Later optional candidates: custom tiny model, legacy Precise/Mycroft-style baselines, or other local engines that can run before streaming starts.

The initial evaluation mode is live microphone testing. Because live-only trials are not fully reproducible, reports must label early metrics as observational.

## Evaluation Metrics

The first reports should capture:

- Endpoint type: Mac Studio or Raspberry Pi 5.
- Microphone identity and placement notes.
- Wake-word engine and phrase track.
- Trigger confidence when the engine provides it.
- Estimated time from phrase start to trigger.
- Time from trigger to first transcript event.
- CPU and memory during idle listening and active streaming.
- False accepts during idle listening windows.
- Missed detections during manual trials.
- Setup friction, reliability notes, and failure modes.

## Demo Milestones

Milestone 1: Mac Studio endpoint path.

```text
Start endpoint on Mac Studio.
Select one wake-word engine and phrase track.
Listen locally.
Detect wake word.
Open post-trigger session to Azure-hosted gateway.
Stream audio to gateway.
Gateway forwards to Microsoft transcription service.
Display or log live transcript.
End session on silence, timeout, or manual stop.
```

Milestone 2: Raspberry Pi 5 endpoint path.

```text
Move the same USB microphone to the Raspberry Pi 5.
Run the same endpoint flow.
Compare setup friction, latency, CPU, memory, and transcript behavior.
```

Milestone 3: Engine comparison.

```text
Run multiple wake-word engines through the same endpoint interface.
Capture observational metrics.
Drop engines that show poor reliability, excessive resource use, or unacceptable integration constraints.
```

Milestone 4: Surgical-domain phrase.

```text
Add or train a custom phrase track.
Compare it against built-in baseline phrases.
Assess whether the phrase is operationally plausible for a surgical-suite environment.
```

## Initial Repo Shape

The repo should start with documentation and scaffolding that makes the architecture explicit:

```text
README.md
docs/
  architecture.md
  wake-word-evaluation.md
  azure-gateway.md
  hardware.md
  superpowers/specs/2026-05-11-wake-word-design.md
endpoint/
  README.md
gateway/
  README.md
eval/
  README.md
```

The design spec is the source of truth for the first implementation plan. Supporting docs can be added as the implementation plan turns these decisions into concrete setup steps and code.

## Implementation Defaults

Endpoint:

- Prefer Python first for rapid iteration on Mac Studio and Raspberry Pi 5.
- Keep wake-word engine interfaces narrow so future C/C++ or Rust endpoints remain possible.
- Use configuration profiles for endpoint type, microphone device, wake engine, phrase track, gateway URL, and run metadata.

Gateway:

- Prefer a websocket-based streaming API between endpoint and gateway.
- Use Azure-hosted deployment from the start.
- Keep Microsoft/Azure transcription behind a gateway adapter so later Azure service choices can be changed without rewriting endpoints.

Configuration:

- Use a structured configuration format such as YAML or TOML.
- Keep environment-specific secrets out of committed config files.

## Out Of Scope For The First Spec

- Clinical note generation.
- EHR integration.
- HIPAA production compliance claims.
- Always-streaming ambient audio.
- Simultaneous Mac/Pi microphone comparison.
- Production hardware selection for surgical suites.
- Reproducible recorded fixture evaluation.

## Open Risks

- Wake-word performance observed with a live USB microphone may not predict performance in a real surgical suite.
- Raspberry Pi 5 microphone and audio driver behavior may differ enough from the Mac Studio to complicate direct comparison.
- Custom surgical-domain phrase support may be constrained by vendor licensing, model training workflow, or model quality.
- Azure real-time transcription service choice may affect protocol design, latency, and cost.
- A credible demo still needs careful wording: it validates architecture and early behavior, not clinical readiness.
