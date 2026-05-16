from pathlib import Path

from typer.testing import CliRunner
from wake_word_endpoint import cli


def write_config(path: Path) -> None:
    path.write_text(
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


def test_run_builds_microphone_endpoint_from_config(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    created: dict[str, object] = {}

    class RecordingSource:
        def __init__(self, device, sample_rate_hz, channels, frame_duration_ms):
            created["source"] = {
                "device": device,
                "sample_rate_hz": sample_rate_hz,
                "channels": channels,
                "frame_duration_ms": frame_duration_ms,
            }

    class RecordingGateway:
        def __init__(self, url, endpoint_id, token):
            created["gateway"] = {
                "url": url,
                "endpoint_id": endpoint_id,
                "token": token,
            }

    class RecordingController:
        def __init__(self, **kwargs):
            created["controller"] = kwargs

        async def run_once(self, max_listen_frames=None):
            created["max_listen_frames"] = max_listen_frames
            return ["live-event"]

    monkeypatch.setenv("GATEWAY_DEVICE_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "MicrophoneAudioSource", RecordingSource)
    monkeypatch.setattr(cli, "GatewayClient", RecordingGateway)
    monkeypatch.setattr(cli, "EndpointController", RecordingController)
    monkeypatch.setattr(cli, "build_wake_engine", lambda *_args, **_kwargs: "fake-engine")

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            str(config_path),
            "--run-id",
            "live-run",
            "--max-listen-seconds",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert created["source"] == {
        "device": None,
        "sample_rate_hz": 16000,
        "channels": 1,
        "frame_duration_ms": 20,
    }
    assert created["gateway"] == {
        "url": "ws://localhost:8080/v1/audio",
        "endpoint_id": "mac-studio-01",
        "token": "secret-token",
    }
    controller = created["controller"]
    assert isinstance(controller, dict)
    assert controller["endpoint_id"] == "mac-studio-01"
    assert controller["run_id"] == "live-run"
    assert controller["audio_source"] is not None
    assert controller["wake_engine"] == "fake-engine"
    assert controller["max_stream_frames"] == 3000
    assert created["max_listen_frames"] == 100
    assert "live-event" in result.output


def test_run_requires_gateway_token_env(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    monkeypatch.delenv("GATEWAY_DEVICE_TOKEN", raising=False)

    result = CliRunner().invoke(cli.app, ["run", str(config_path)])

    assert result.exit_code != 0
    assert "GATEWAY_DEVICE_TOKEN" in str(result.exception)


def test_run_passes_sherpa_onnx_options_to_engine_builder(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    config_path.write_text(config_path.read_text().replace("engine: fake", "engine: sherpa-onnx"))
    created: dict[str, object] = {}

    class RecordingSource:
        def __init__(self, **_kwargs):
            pass

    class RecordingGateway:
        def __init__(self, **_kwargs):
            pass

    class RecordingController:
        def __init__(self, **kwargs):
            created["controller"] = kwargs

        async def run_once(self, max_listen_frames=None):
            return []

    def recording_engine_builder(engine, phrase_track, **kwargs):
        created["engine"] = engine
        created["phrase_track"] = phrase_track
        created["engine_kwargs"] = kwargs
        return "sherpa-engine"

    monkeypatch.setenv("GATEWAY_DEVICE_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "MicrophoneAudioSource", RecordingSource)
    monkeypatch.setattr(cli, "GatewayClient", RecordingGateway)
    monkeypatch.setattr(cli, "EndpointController", RecordingController)
    monkeypatch.setattr(cli, "build_wake_engine", recording_engine_builder)

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            str(config_path),
            "--sherpa-model-dir",
            "/models/kws",
            "--sherpa-keywords-file",
            "/models/kws/keywords.txt",
            "--sherpa-num-threads",
            "4",
            "--sherpa-provider",
            "cpu",
        ],
    )

    assert result.exit_code == 0
    assert created["engine"] == "sherpa-onnx"
    assert created["phrase_track"] == "builtin-baseline"
    assert created["engine_kwargs"] == {
        "openwakeword_model": "hey_jarvis",
        "openwakeword_threshold": 0.5,
        "porcupine_keyword": "picovoice",
        "porcupine_access_key_env": "PORCUPINE_ACCESS_KEY",
        "microsoft_keyword_table": None,
        "microsoft_sample_rate_hz": 16000,
        "microsoft_channels": 1,
        "sherpa_model_dir": "/models/kws",
        "sherpa_keywords_file": "/models/kws/keywords.txt",
        "sherpa_num_threads": 4,
        "sherpa_provider": "cpu",
    }


def test_run_passes_microsoft_custom_keyword_options_to_engine_builder(monkeypatch, tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text()
        .replace("engine: fake", "engine: microsoft-custom-keyword")
        .replace("phrase_track: builtin-baseline", "phrase_track: custom-hey-sentinel")
    )
    created: dict[str, object] = {}

    class RecordingSource:
        def __init__(self, **_kwargs):
            pass

    class RecordingGateway:
        def __init__(self, **_kwargs):
            pass

    class RecordingController:
        def __init__(self, **kwargs):
            created["controller"] = kwargs

        async def run_once(self, max_listen_frames=None):
            return []

    def recording_engine_builder(engine, phrase_track, **kwargs):
        created["engine"] = engine
        created["phrase_track"] = phrase_track
        created["engine_kwargs"] = kwargs
        return "microsoft-engine"

    monkeypatch.setenv("GATEWAY_DEVICE_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "MicrophoneAudioSource", RecordingSource)
    monkeypatch.setattr(cli, "GatewayClient", RecordingGateway)
    monkeypatch.setattr(cli, "EndpointController", RecordingController)
    monkeypatch.setattr(cli, "build_wake_engine", recording_engine_builder)

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            str(config_path),
            "--microsoft-keyword-table",
            "/models/microsoft-custom-keyword/hey-sentinel.table",
        ],
    )

    assert result.exit_code == 0
    assert created["engine"] == "microsoft-custom-keyword"
    assert created["phrase_track"] == "custom-hey-sentinel"
    assert created["engine_kwargs"] == {
        "openwakeword_model": "hey_jarvis",
        "openwakeword_threshold": 0.5,
        "porcupine_keyword": "picovoice",
        "porcupine_access_key_env": "PORCUPINE_ACCESS_KEY",
        "microsoft_keyword_table": "/models/microsoft-custom-keyword/hey-sentinel.table",
        "microsoft_sample_rate_hz": 16000,
        "microsoft_channels": 1,
        "sherpa_model_dir": None,
        "sherpa_keywords_file": None,
        "sherpa_num_threads": 2,
        "sherpa_provider": "cpu",
    }
