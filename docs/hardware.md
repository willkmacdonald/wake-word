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

## Milestone 1 Hardware Verification

The Mac Studio microphone smoke test on May 12, 2026 captured 50 frames from
`endpoint/configs/mac.example.yaml` with 32,000 total bytes at 16 kHz mono.

The Raspberry Pi audio script has been syntax-checked locally with:

```bash
bash -n scripts/pi/check_audio.sh
```

Actual Pi microphone capture still needs to be run on the Raspberry Pi 5 after
fresh setup.

## Live Endpoint Run

Once microphone profiling is acceptable, start the gateway and run the real
endpoint path:

```bash
. .venv/bin/activate
export GATEWAY_DEVICE_TOKEN=<gateway device token>
wake-endpoint run endpoint/configs/pi.example.yaml --run-id pi-live-001 --max-listen-seconds 30
```

The command uses the microphone and the wake engine named in the endpoint config.
The example configs use `fake` so you can verify capture and gateway streaming
before installing OpenWakeWord or Porcupine.
