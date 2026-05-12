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
sudo apt install -y git python3-full python3-venv python3-pip build-essential pkg-config usbutils alsa-utils portaudio19-dev ffmpeg sox
```

Clone or copy this repository onto the Pi, then run the remaining commands from
the repository root:

```bash
git clone <repository-url> wake-word
cd wake-word
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
