# Wake-Word Roadmap

This roadmap describes the practical path from the current Mac Studio wake-word
baseline to a portable demo architecture. It is not a clinical validation plan.
All live microphone results are observational until the evaluation lab adds
fixed fixtures and replayable noise conditions.

## Current Baseline

Use Microsoft Custom Keyword with the `Hey Computer` `.table` model as the
baseline wake-word path.

Evidence recorded in `eval/live_trials/2026-05-16-mac-microsoft-hey-computer.yaml`:

- Mac Studio endpoint with local mock gateway.
- Four spoken trials detected immediately on the first `Hey Computer` attempt.
- A 60 second idle false-accept test passed with no trigger.
- The visible transcript response appeared around seven seconds because the
  current demo streams a fixed five second post-trigger clip before finalizing.
  That is not wake-detection latency.

Candidates no longer on the primary path:

- OpenWakeWord `Hey Jarvis`: abandon for this project.
- Sherpa-ONNX `Hey Computer`: keep only as a historical/offline reference.
- Microsoft Custom Keyword `Hey Sentinel`: viable but less reliable than
  `Hey Computer`.
- Porcupine: paused because account/licensing workflow was not a good fit for
  this experiment.

## Guiding Decisions

- Keep wake detection local. The endpoint must not stream microphone audio
  before local wake activation.
- Keep Microsoft/Azure as the default cloud provider unless a better reason
  emerges.
- Reuse existing Azure shared services whenever possible:
  `shared-services-rg/shared-services-env`, `wkmsharedservicesacr`, and
  `wkm-shared-kv`.
- Optimize cloud cost. Use `minReplicas=1` only for active demos or latency
  measurements; park at `minReplicas=0` when idle.
- Keep Python unless Raspberry Pi profiling proves runtime reliability or
  packaging is a real problem. Rust is a later endpoint-runtime option, not a
  wake-quality fix.
- Treat LiveKit as a later post-wake transport candidate, not a wake-word
  replacement.

## Phase 1: Lock The Mac Baseline

Goal: make the Mac Studio path repeatable enough to use as the reference
endpoint.

Work:

1. Run one additional Mac Studio `Hey Computer` smoke pass after a fresh clone
   or clean environment setup.
2. Confirm `wake.detected` appears immediately on first utterance.
3. Confirm 60 seconds of idle listening has zero false accepts.
4. Record the result as a new live-trial YAML if the microphone, room, or code
   has changed materially.
5. Keep `models/microsoft-custom-keyword/*.table` local and ignored by git.

Exit criteria:

- `Hey Computer` remains the Mac baseline.
- The README and `custom-keyword.md` commands work from a clean local setup.
- No cloud dependency is needed before wake detection.

## Phase 2: Raspberry Pi Endpoint Comparison

Goal: determine whether the same local endpoint architecture works on the
Raspberry Pi 5.

Work:

1. Wipe/setup the Raspberry Pi 5 with Raspberry Pi OS Lite 64-bit.
2. Use hostname `wakepi-01` and prefer Ethernet during first tests.
3. Install system audio dependencies from `docs/hardware.md`.
4. Clone the repo onto the Pi.
5. Copy `models/microsoft-custom-keyword/hey-computer.table` to the Pi outside
   git.
6. Run `scripts/pi/check_audio.sh`.
7. Run `wake-endpoint audio-profile endpoint/configs/pi.example.yaml --frames 200`.
8. Create or update a Pi Microsoft Custom Keyword config if needed.
9. Run the same live trial protocol:
   - 60 seconds idle, no false accepts.
   - Five spoken `Hey Computer` attempts.
   - Record misses and visible response timing.
10. Add a Pi live-trial YAML under `eval/live_trials/`.

Exit criteria:

- Pi microphone capture is stable enough for wake-word testing.
- Pi can run Microsoft Custom Keyword locally.
- Pi result is good enough to compare against Mac, or we have a clear hardware
  or runtime reason it is not.

## Phase 3: Azure Gateway End-To-End

Goal: validate the full post-wake path through Azure without changing the local
wake decision.

Work:

1. Reverify Azure Dev subscription context and shared services.
2. Build and push the gateway container to `wkmsharedservicesacr`.
3. Deploy or update the gateway Container App in `shared-services-rg`.
4. Use Key Vault-backed secrets for Azure Speech and gateway device token.
5. Verify `/healthz` and `/metrics`.
6. Run Mac Studio endpoint against the Azure gateway with Microsoft
   `Hey Computer`.
7. Confirm post-wake audio reaches Azure Speech and transcript events return.
8. Record trigger-to-first-transcript timing separately from wake-detection
   timing.
9. Document the parking command or parameter set for `minReplicas=0`.

Exit criteria:

- Local endpoint still streams no audio before wake.
- Azure gateway receives only post-trigger audio.
- Transcript events return through the deployed gateway.
- Cost posture is explicit for active demo vs parked state.

## Phase 4: Demo Runtime Improvements

Goal: make the demo feel like an ambient assistant rather than a one-shot test
command.

Work:

1. Add continuous/re-arm mode after a completed session.
2. Add a short local pre-roll buffer so audio immediately after wake is not
   clipped.
3. Stream partial transcription events instead of waiting for a fixed
   post-trigger clip to finish.
4. Separate wake latency, gateway connection latency, and first-transcript
   latency in CLI output.
5. Add run IDs and trial metadata that are easy to copy into live-trial YAML.
6. Keep one-shot mode for controlled experiments.

Exit criteria:

- The demo can keep listening across multiple wake sessions.
- The user sees transcript feedback before the fixed session window ends.
- Measurements clearly distinguish local wake performance from cloud
  transcription latency.

## Phase 5: Reproducible Evaluation Lab

Goal: move beyond observational live trials before making stronger claims about
engine quality.

Work:

1. Add recorded positive fixtures for `Hey Computer`.
2. Add negative speech fixtures that should not trigger.
3. Add silence and idle-room samples for false-accept testing.
4. Add noise overlays with controllable SNR.
5. Add surgical-suite-like noise profiles when legally and practically
   available.
6. Run raw-audio baseline measurements before any preprocessing.
7. Test optional preprocessing as an explicit experiment, not a default.

Exit criteria:

- Mac and Pi results can be compared from replayable input audio.
- False accepts and misses are measured with repeatable fixtures.
- Any preprocessing decision is backed by before/after data.

## Later Options

LiveKit:

- Revisit after the Azure gateway path is working.
- Evaluate it as a post-wake realtime media/session layer.
- Do not treat it as a wake-word engine.

Rust endpoint:

- Revisit only if Pi profiling shows Python capture/runtime problems, service
  packaging becomes painful, or we need a smaller long-running daemon.
- Do not expect Rust to improve Microsoft Custom Keyword model quality.

Additional wake engines:

- Only add another engine if Microsoft Custom Keyword fails on the Pi or the
  custom keyword workflow becomes unacceptable.
- Any new candidate must run locally before audio streaming starts.

## Immediate Next Step

Start Phase 2: Raspberry Pi endpoint comparison.

The first useful action is to wipe/setup the Pi, clone the repo, copy
`hey-computer.table`, and run the Pi audio checks before attempting wake-word
detection.
