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
