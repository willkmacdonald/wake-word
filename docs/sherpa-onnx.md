# Sherpa-ONNX Keyword Spotting

Sherpa-ONNX is the current no-account local wake-word candidate. It runs
offline, uses ONNX models, and supports open-vocabulary keyword spotting without
training a custom model.

Use it when Microsoft Custom Keyword is blocked by portal training or eligibility
gating and when Picovoice/Porcupine account requirements are not a good fit.

References:

- https://k2-fsa.github.io/sherpa/onnx/kws/index.html
- https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/keyword-spotter.py

## Install

From the repository root:

```bash
uv pip install -e ".[sherpa]"
```

## Download English KWS Model

Use the English GigaSpeech keyword spotting model first:

```bash
mkdir -p models/sherpa-onnx
cd models/sherpa-onnx

curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2
tar xjf sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2
cd ../..
```

Model directory:

```text
models/sherpa-onnx/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01
```

## Create Keywords File

Sherpa keyword spotting uses tokenized keyword lines. The text form can include:

- `:N.N` boosting score
- `#N.N` trigger threshold
- `@ORIGINAL PHRASE` label

Create a raw keyword file:

```bash
cat > /tmp/sherpa-keywords-raw.txt <<'EOF'
HEY SENTINEL :2.0 #0.35 @HEY SENTINEL
WAKE SENTINEL :2.0 #0.35 @WAKE SENTINEL
HEY COMPUTER :2.0 #0.35 @HEY COMPUTER
EOF
```

Tokenize it with the model vocabulary:

```bash
MODEL_DIR="models/sherpa-onnx/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"

uv run sherpa-onnx-cli text2token \
  --tokens "$MODEL_DIR/tokens.txt" \
  --tokens-type bpe \
  /tmp/sherpa-keywords-raw.txt \
  /tmp/sherpa-keywords.txt
```

Inspect the output:

```bash
cat /tmp/sherpa-keywords.txt
```

## Endpoint Config

Create a temporary endpoint config:

```bash
cp endpoint/configs/mac.example.yaml /tmp/mac.sherpa.yaml
perl -0pi -e 's/engine: fake/engine: sherpa-onnx/' /tmp/mac.sherpa.yaml
perl -0pi -e 's/max_seconds: 60/max_seconds: 5/' /tmp/mac.sherpa.yaml
```

Confirm:

```bash
grep -A4 -B2 'wake_word' /tmp/mac.sherpa.yaml
grep -A3 '^session:' /tmp/mac.sherpa.yaml
```

## Run Local Trial

Keep the local mock gateway running in another terminal:

```bash
cd gateway
GATEWAY_DEVICE_TOKEN=dev-token \
GATEWAY_ALLOWED_ENDPOINT_IDS=mac-studio-01 \
TRANSCRIPTION_MODE=mock \
npm run dev
```

Run the sherpa endpoint:

```bash
MODEL_DIR="models/sherpa-onnx/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01"

GATEWAY_DEVICE_TOKEN=dev-token \
uv run wake-endpoint run /tmp/mac.sherpa.yaml \
  --run-id mac-sherpa-001 \
  --max-listen-seconds 30 \
  --sherpa-model-dir "$MODEL_DIR" \
  --sherpa-keywords-file /tmp/sherpa-keywords.txt
```

Say one of the configured phrases:

```text
Hey Sentinel
Wake Sentinel
Hey Computer
```

If it detects, the endpoint streams five seconds of post-trigger audio and then
prints `session.accepted`, `transcript.final`, and `session.ended`.

Check gateway metrics:

```bash
curl -fsS http://127.0.0.1:8080/metrics
```

## Tuning Notes

If detection is too weak, increase the boosting score, lower the trigger
threshold, or try a phrase with more distinctive syllables. If false triggers
appear during idle listening, lower the boosting score or raise the trigger
threshold.

The sherpa docs note that lower thresholds trigger more easily and larger
boosting scores make keyword paths more likely to survive beam search. Treat
these results as observational-live until recorded fixture tests are added.
