"""Configuration loading utilities."""

import json
from pathlib import Path

from nanoclaw_mini.config.schema import Config


# Global variable to store current config path (for multi-instance support)
_current_config_path: Path | None = None
_LEGACY_CONFIG_PATH = Path.home() / ".nanobot" / "config.json"


def set_config_path(path: Path) -> None:
    """Set the current config path (used to derive data directory)."""
    global _current_config_path
    _current_config_path = path


def get_config_path() -> Path:
    """Get the configuration file path."""
    if _current_config_path:
        return _current_config_path
    return Path.home() / ".nanoclaw-mini" / "config.json"


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file or create default.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Loaded configuration object.
    """
    global _current_config_path

    path = config_path or get_config_path()
    candidate = path
    if config_path is None and not candidate.exists() and _LEGACY_CONFIG_PATH.exists():
        candidate = _LEGACY_CONFIG_PATH

    _current_config_path = candidate

    if candidate.exists():
        try:
            # Accept both plain UTF-8 and UTF-8 with BOM from Windows editors.
            with open(candidate, encoding="utf-8-sig") as f:
                data = json.load(f)
            data = _migrate_config(data)
            return Config.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {candidate}: {e}")
            print("Using default configuration.")

    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Optional path to save to. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(by_alias=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _migrate_config(data: dict) -> dict:
    """Migrate old config formats to current."""
    # Move tools.exec.restrictToWorkspace → tools.restrictToWorkspace
    tools = data.get("tools", {})
    exec_cfg = tools.get("exec", {})
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")

    channels = data.pop("channels", {})
    interaction = data.setdefault("interaction", {})
    if isinstance(channels, dict):
        if "sendProgress" in channels and "sendProgress" not in interaction:
            interaction["sendProgress"] = channels["sendProgress"]
        if "sendToolHints" in channels and "sendToolHints" not in interaction:
            interaction["sendToolHints"] = channels["sendToolHints"]

    agents = data.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    if defaults.get("provider") in {None, "", "auto", "openai"}:
        defaults["provider"] = "openai_codex"
    if defaults.get("model") in {None, "", "gpt-4.1-mini"}:
        defaults["model"] = "openai-codex/gpt-5.1-codex"

    providers = data.setdefault("providers", {})
    if isinstance(providers, dict):
        openai_codex = providers.get("openaiCodex", providers.get("openai_codex", {}))
        data["providers"] = {"openaiCodex": openai_codex if isinstance(openai_codex, dict) else {}}

    return data
