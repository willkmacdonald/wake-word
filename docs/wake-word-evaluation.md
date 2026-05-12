# Wake-Word Evaluation

The first evaluation mode is live microphone testing. Reports must mark metrics as observational because the input audio is not replayed from fixed fixtures.

## OpenWakeWord Track

OpenWakeWord is the first open-source candidate. Start with a built-in model to evaluate integration, CPU, memory, and false accepts before investing in a surgical-domain phrase.

Install with:

```bash
python -m pip install -e ".[openwakeword]"
```

Download the pre-trained models once on each evaluation machine before using
`OpenWakeWordEngine.from_default_model()`:

```bash
python -c "import openwakeword; openwakeword.utils.download_models()"
```

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

Evaluation harnesses should read `PICOVOICE_ACCESS_KEY` and pass it explicitly to
`PorcupineEngine.from_keywords()`. The adapter does not read environment
variables directly.

Porcupine requires 16 kHz mono frames with exactly `porcupine.frame_length`
samples. Configure endpoint frame duration to match the selected Porcupine engine
or add a reframing buffer before using this adapter.

## Live Trial Protocol

For each run:

1. Record endpoint type, microphone, wake engine, phrase track, and room notes.
2. Run idle listening and count false accepts.
3. Speak the wake phrase ten times and count missed detections.
4. Record time from trigger to first transcript when available.
5. Mark results as `observational-live`.

Use `eval/live_trial_template.yaml` as the run record format.

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
