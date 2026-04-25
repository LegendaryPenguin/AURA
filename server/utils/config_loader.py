from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when configuration files are missing or malformed."""


REQUIRED_TOP_LEVEL_KEYS: dict[str, set[str]] = {
    "models.yaml": {"global", "paths", "vlm", "audio", "segmentation", "depth", "generation", "agents"},
    "pipeline.yaml": {"orchestrator", "timeouts", "preprocess", "snapshot", "streaming"},
    "server.yaml": {"server", "ssl", "cors", "rate_limit", "health"},
    "demo.yaml": {"demo", "fallback", "mock", "telemetry"},
}


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"Top-level YAML object in {config_path} must be a mapping")
    return raw


def validate_required_keys(path: str | Path, config: dict[str, Any]) -> None:
    config_name = Path(path).name
    required_keys = REQUIRED_TOP_LEVEL_KEYS.get(config_name)
    if required_keys is None:
        return

    missing = sorted(key for key in required_keys if key not in config)
    if missing:
        raise ConfigError(f"Missing required keys in {config_name}: {', '.join(missing)}")


def load_and_validate(path: str | Path) -> dict[str, Any]:
    config = load_yaml_config(path)
    validate_required_keys(path, config)
    return config


def load_all_project_configs(config_dir: str | Path) -> dict[str, dict[str, Any]]:
    config_root = Path(config_dir)
    configs: dict[str, dict[str, Any]] = {}
    for config_name in REQUIRED_TOP_LEVEL_KEYS:
        config_path = config_root / config_name
        configs[config_name] = load_and_validate(config_path)
    return configs
