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
