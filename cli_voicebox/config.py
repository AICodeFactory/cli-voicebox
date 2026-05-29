"""JSON configuration loader for cli-voicebox."""

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field


class CliConfig(BaseModel):
    """CLI configuration loaded from JSON."""

    voicebox_url: str = Field(default="http://127.0.0.1:17493")
    timeout_seconds: int = Field(default=600)

    def apply_env_overrides(self) -> "CliConfig":
        """Apply environment variable overrides."""
        data = self.model_dump()
        url = os.environ.get("VOICEBOX_BASE_URL")
        if url:
            data["voicebox_url"] = url.rstrip("/")
        timeout = os.environ.get("VOICEBOX_TIMEOUT")
        if timeout:
            try:
                data["timeout_seconds"] = int(timeout)
            except ValueError:
                pass
        return CliConfig(**data)

    @property
    def base_url(self) -> str:
        return self.voicebox_url.rstrip("/")


def load_config(config_path: str | Path) -> CliConfig:
    """Load configuration from a JSON file."""
    from cli_voicebox.user_paths import ensure_config_exists

    path = ensure_config_exists(Path(config_path))

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")

    return CliConfig(**data).apply_env_overrides()
