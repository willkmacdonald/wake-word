# Endpoint

The endpoint runs on the Mac Studio or Raspberry Pi 5. It owns microphone capture, local wake-word detection, post-trigger streaming, and local run metadata.

The endpoint does not own Azure Speech or Azure OpenAI credentials.

## Raspberry Pi 5 Bring-Up

1. Flash Raspberry Pi OS Lite 64-bit.
2. Enable SSH and set hostname `wakepi-01`.
3. Install dependencies from `docs/hardware.md`, then clone or copy this repository to the Pi and `cd` to the repository root.
4. Run `scripts/pi/check_audio.sh`.
5. Create a Python virtual environment and install this repo.
6. Run `wake-endpoint config-check endpoint/configs/pi.example.yaml`.
7. Run `wake-endpoint mic-probe endpoint/configs/pi.example.yaml --frames 50`.
