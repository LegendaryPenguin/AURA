from __future__ import annotations

from pathlib import Path

import pytest

from server.utils.config_loader import ConfigError, load_all_project_configs, load_and_validate


def test_load_and_validate_accepts_valid_models_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        "\n".join(
            [
                "global: {}",
                "paths: {}",
                "vlm: {}",
                "audio: {}",
                "segmentation: {}",
                "depth: {}",
                "generation: {}",
                "agents: {}",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_and_validate(config_path)
    assert set(loaded.keys()) == {
        "global",
        "paths",
        "vlm",
        "audio",
        "segmentation",
        "depth",
        "generation",
        "agents",
    }


def test_load_and_validate_rejects_missing_required_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "server.yaml"
    config_path.write_text("server: {}\nssl: {}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Missing required keys in server.yaml"):
        load_and_validate(config_path)


def test_load_and_validate_rejects_invalid_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text("orchestrator: [broken", encoding="utf-8")

    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_and_validate(config_path)


def test_load_all_project_configs_loads_all_required_files(tmp_path: Path) -> None:
    (tmp_path / "models.yaml").write_text(
        "global: {}\npaths: {}\nvlm: {}\naudio: {}\nsegmentation: {}\ndepth: {}\ngeneration: {}\nagents: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "pipeline.yaml").write_text(
        "orchestrator: {}\ntimeouts: {}\npreprocess: {}\nsnapshot: {}\nstreaming: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "server.yaml").write_text(
        "server: {}\nssl: {}\ncors: {}\nrate_limit: {}\nhealth: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "demo.yaml").write_text(
        "demo: {}\nfallback: {}\nmock: {}\ntelemetry: {}\n",
        encoding="utf-8",
    )

    loaded = load_all_project_configs(tmp_path)
    assert set(loaded.keys()) == {"models.yaml", "pipeline.yaml", "server.yaml", "demo.yaml"}
