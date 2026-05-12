from __future__ import annotations

from pathlib import Path

import typer
import yaml

from wake_word_eval.trial import LiveTrial

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Wake-word live-trial evaluation reports."""


def summarize_trial(trial: LiveTrial) -> dict[str, object]:
    return {
        "run_id": trial.run_id,
        "endpoint_type": trial.endpoint_type,
        "microphone": trial.microphone,
        "wake_engine": trial.wake_engine,
        "phrase_track": trial.phrase_track,
        "metric_quality": "observational-live",
        "false_accepts": trial.false_accepts,
        "missed_detections": trial.missed_detections,
        "trigger_to_first_transcript_ms": trial.trigger_to_first_transcript_ms,
        "notes": trial.notes,
    }


@app.command()
def summarize(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    trial = LiveTrial(**data)
    typer.echo(yaml.safe_dump(summarize_trial(trial), sort_keys=False))
