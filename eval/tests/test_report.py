from typer.testing import CliRunner
from wake_word_eval.report import app, load_trial, summarize_trial
from wake_word_eval.trial import LiveTrial

runner = CliRunner()


def test_summarize_trial_marks_live_metrics_observational():
    trial = LiveTrial(
        run_id="mac-openwakeword-001",
        endpoint_type="mac-studio",
        microphone="usb-mic-a",
        wake_engine="openwakeword",
        phrase_track="builtin-baseline",
        false_accepts=0,
        missed_detections=1,
        trigger_to_first_transcript_ms=850,
        notes="quiet office",
    )

    summary = summarize_trial(trial)

    assert summary["run_id"] == "mac-openwakeword-001"
    assert summary["metric_quality"] == "observational-live"
    assert summary["missed_detections"] == 1


def test_report_cli_summarize_keeps_observational_metric_quality(tmp_path):
    trial_path = tmp_path / "trial.yaml"
    trial_path.write_text(
        "\n".join(
            [
                "run_id: pi-porcupine-001",
                "endpoint_type: raspberry-pi-5",
                "microphone: usb-mic-a",
                "wake_engine: porcupine",
                "phrase_track: surgical-domain",
                "false_accepts: 0",
                "missed_detections: 0",
                "trigger_to_first_transcript_ms: 920",
                "notes: quiet office",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["summarize", str(trial_path)])

    assert result.exit_code == 0
    assert "metric_quality: observational-live" in result.stdout


def test_load_trial_rejects_empty_yaml(tmp_path):
    trial_path = tmp_path / "empty.yaml"
    trial_path.write_text("", encoding="utf-8")

    result = runner.invoke(app, ["summarize", str(trial_path)])

    assert result.exit_code != 0
    assert "must contain a YAML mapping" in result.stderr


def test_load_trial_rejects_non_mapping_yaml(tmp_path):
    trial_path = tmp_path / "list.yaml"
    trial_path.write_text("- not\n- a mapping\n", encoding="utf-8")

    result = runner.invoke(app, ["summarize", str(trial_path)])

    assert result.exit_code != 0
    assert "must contain a YAML mapping" in result.stderr


def test_load_trial_rejects_wrong_metric_types(tmp_path):
    trial_path = tmp_path / "bad-types.yaml"
    trial_path.write_text(
        "\n".join(
            [
                "run_id: pi-porcupine-001",
                "endpoint_type: raspberry-pi-5",
                "microphone: usb-mic-a",
                "wake_engine: porcupine",
                "phrase_track: surgical-domain",
                "false_accepts: many",
                "missed_detections: 0",
                "trigger_to_first_transcript_ms: 920",
                "notes: quiet office",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["summarize", str(trial_path)])

    assert result.exit_code != 0
    assert "false_accepts must be an integer" in result.stderr


def test_load_trial_rejects_unknown_fields(tmp_path):
    trial_path = tmp_path / "extra.yaml"
    trial_path.write_text(
        "\n".join(
            [
                "run_id: pi-porcupine-001",
                "endpoint_type: raspberry-pi-5",
                "microphone: usb-mic-a",
                "wake_engine: porcupine",
                "phrase_track: surgical-domain",
                "false_accepts: 0",
                "missed_detections: 0",
                "trigger_to_first_transcript_ms: null",
                "notes: quiet office",
                "metric_quality: lab-reproducible",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["summarize", str(trial_path)])

    assert result.exit_code != 0
    assert "unexpected field" in result.stderr


def test_load_trial_accepts_null_trigger_latency(tmp_path):
    trial_path = tmp_path / "trial.yaml"
    trial_path.write_text(
        "\n".join(
            [
                "run_id: pi-porcupine-001",
                "endpoint_type: raspberry-pi-5",
                "microphone: usb-mic-a",
                "wake_engine: porcupine",
                "phrase_track: surgical-domain",
                "false_accepts: 0",
                "missed_detections: 0",
                "trigger_to_first_transcript_ms: null",
                "notes: quiet office",
            ]
        ),
        encoding="utf-8",
    )

    trial = load_trial(trial_path)

    assert trial.trigger_to_first_transcript_ms is None
