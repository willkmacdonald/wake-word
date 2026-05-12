from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from wake_word_endpoint.config import load_config

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Wake-word endpoint command line tools."""


@app.command()
def config_check(config: Path) -> None:
    """Load an endpoint config and print the effective endpoint identity."""
    loaded = load_config(config)
    print(
        {
            "endpoint_id": loaded.endpoint.id,
            "endpoint_type": loaded.endpoint.type,
            "wake_engine": loaded.wake_word.engine,
            "gateway_url": loaded.gateway.url,
        }
    )
