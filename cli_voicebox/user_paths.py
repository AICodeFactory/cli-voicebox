"""Cross-platform user config directory for cli-voicebox."""

from __future__ import annotations

import json
import os
import sys
from importlib import resources
from pathlib import Path
from typing import Literal

APP_NAME = "voicebox-cli"
CONFIG_FILENAME = "config.json"


def get_platform_kind() -> Literal["macos", "windows", "linux", "other"]:
    system = sys.platform
    if system == "darwin":
        return "macos"
    if system == "win32":
        return "windows"
    if system.startswith("linux"):
        return "linux"
    return "other"


def get_config_dir() -> Path:
    """
    User-level config directory (independent of current working directory).

    macOS / Linux:  ~/.config/voicebox-cli/
    Windows:        %APPDATA%\\voicebox-cli\\
    """
    kind = get_platform_kind()
    if kind == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return (Path(appdata) / APP_NAME).resolve()
        return (Path.home() / "AppData" / "Roaming" / APP_NAME).resolve()

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return (Path(xdg) / APP_NAME).resolve()
    return (Path.home() / ".config" / APP_NAME).resolve()


def get_default_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


def get_config_path_help_lines() -> list[str]:
    """Human-readable config paths for --help."""
    cfg = get_config_dir()
    cfg_file = get_default_config_path()
    return [
        "DEFAULT CONFIG (used when -c/--config is omitted; cwd does not matter)",
        "",
        f"  Config dir:   {cfg}",
        f"  config.json:  {cfg_file}",
        "",
        "  Any --help auto-creates the directory and config.json if missing.",
        "  Override:  -c /path/to/config.json",
        "  Env:       VOICEBOX_CLI_CONFIG=/path/to/config.json",
    ]


def _read_bundled_example() -> dict:
    try:
        ref = resources.files("cli_voicebox").joinpath("config.example.json")
        text = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError):
        fallback = Path(__file__).resolve().parent / "config.example.json"
        text = fallback.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Bundled config example must be a JSON object")
    return data


def ensure_user_config_layout() -> None:
    get_config_dir().mkdir(parents=True, exist_ok=True)


def ensure_user_config_if_missing() -> bool:
    """Returns True if config.json was newly created."""
    ensure_user_config_layout()
    if get_default_config_path().exists():
        return False
    init_user_config(force=False)
    return True


def init_user_config(force: bool = False) -> Path:
    config_path = get_default_config_path()
    ensure_user_config_layout()

    if config_path.exists() and not force:
        return config_path

    example = _read_bundled_example()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(example, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return config_path


def resolve_config_path(explicit: str | None) -> Path:
    if explicit is not None:
        path = Path(explicit).expanduser()
        return path.resolve()

    env_path = os.environ.get("VOICEBOX_CLI_CONFIG")
    if env_path:
        return Path(env_path).expanduser().resolve()

    return init_user_config(force=False)


def ensure_config_exists(path: Path) -> Path:
    if path.exists():
        return path

    if path.resolve() == get_default_config_path().resolve():
        return init_user_config(force=False)

    raise FileNotFoundError(
        f"Config file not found: {path}\n"
        f"Default user config: {get_default_config_path()}\n"
        f"Run: voicebox-cli init"
    )
