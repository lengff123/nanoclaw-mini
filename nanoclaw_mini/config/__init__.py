"""Configuration module for nanoclaw-mini."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "Config",
    "load_config",
    "get_config_path",
    "get_data_dir",
    "get_runtime_subdir",
    "get_media_dir",
    "get_cron_dir",
    "get_logs_dir",
    "get_workspace_path",
    "get_cli_history_path",
    "get_legacy_sessions_dir",
]

if TYPE_CHECKING:
    from nanoclaw_mini.config.loader import get_config_path, load_config
    from nanoclaw_mini.config.paths import (
        get_cli_history_path,
        get_cron_dir,
        get_data_dir,
        get_legacy_sessions_dir,
        get_logs_dir,
        get_media_dir,
        get_runtime_subdir,
        get_workspace_path,
    )
    from nanoclaw_mini.config.schema import Config


def __getattr__(name: str) -> Any:
    """Lazily expose config helpers without importing the full config stack."""
    if name == "Config":
        from nanoclaw_mini.config.schema import Config

        return Config
    if name in {"get_config_path", "load_config"}:
        from nanoclaw_mini.config import loader

        return getattr(loader, name)
    if name in {
        "get_cli_history_path",
        "get_cron_dir",
        "get_data_dir",
        "get_legacy_sessions_dir",
        "get_logs_dir",
        "get_media_dir",
        "get_runtime_subdir",
        "get_workspace_path",
    }:
        from nanoclaw_mini.config import paths

        return getattr(paths, name)
    raise AttributeError(name)
