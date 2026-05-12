from __future__ import annotations

from pathlib import Path

import typer
import yaml
from yaml import YAMLError

from wake_word_eval.trial import LiveTrial

app = typer.Typer(no_args_is_help=True)

TRIAL_FIELDS = {
    "run_id",
    "endpoint_type",
    "microphone",
    "wake_engine",
    "phrase_track",
    "false_accepts",
    "missed_detections",
    "trigger_to_first_transcript_ms",
    "notes",
}


class TrialLoadError(ValueError):
    pass


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


def _require_string(data: dict[str, object], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or value == "":
        raise TrialLoadError(f"{field} must be a non-empty string")
    return value


def _require_integer(data: dict[str, object], field: str) -> int:
    value = data[field]
    if not isinstance(value, int) or isinstance(value, bool):
        raise TrialLoadError(f"{field} must be an integer")
    return value


def _optional_integer(data: dict[str, object], field: str) -> int | None:
    value = data[field]
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise TrialLoadError(f"{field} must be an integer or null")
    return value


def load_trial(path: Path) -> LiveTrial:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise TrialLoadError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise TrialLoadError(f"{path} must contain a YAML mapping")

    missing = TRIAL_FIELDS - data.keys()
    if missing:
        raise TrialLoadError(f"{path} is missing required field: {sorted(missing)[0]}")

    unexpected = data.keys() - TRIAL_FIELDS
    if unexpected:
        raise TrialLoadError(f"{path} has unexpected field: {sorted(unexpected)[0]}")

    return LiveTrial(
        run_id=_require_string(data, "run_id"),
        endpoint_type=_require_string(data, "endpoint_type"),
        microphone=_require_string(data, "microphone"),
        wake_engine=_require_string(data, "wake_engine"),
        phrase_track=_require_string(data, "phrase_track"),
        false_accepts=_require_integer(data, "false_accepts"),
        missed_detections=_require_integer(data, "missed_detections"),
        trigger_to_first_transcript_ms=_optional_integer(data, "trigger_to_first_transcript_ms"),
        notes=_require_string(data, "notes"),
    )


@app.command()
def summarize(path: Path) -> None:
    try:
        trial = load_trial(path)
    except TrialLoadError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(yaml.safe_dump(summarize_trial(trial), sort_keys=False))
