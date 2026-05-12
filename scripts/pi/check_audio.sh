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
