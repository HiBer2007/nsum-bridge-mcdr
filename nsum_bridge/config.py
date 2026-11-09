"""配置读取：`config/nsum_bridge/config.json`（MCDR 插件配置目录）。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "repo": "",
    "branch": "base",
    "git_branch": "main",
    "server_dir": "server",
    "nsum_runtime": "NeoServerUpdateModpack",
    "java": "java",
    "sync_format": "hmcl",
    "auto_install_core": True,
    "launch_on_sync_failure": False,
    "prepare_on_load": False,
    "timeout_seconds": 1800,
}


@dataclass
class Config:
    base_dir: Path
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.raw.get("enabled", True))

    @property
    def repo(self) -> str:
        return str(self.raw.get("repo") or "")

    @property
    def branch(self) -> str:
        return str(self.raw.get("branch") or "base")

    @property
    def git_branch(self) -> str:
        return str(self.raw.get("git_branch") or "")

    @property
    def server_dir(self) -> Path:
        value = self.raw.get("server_dir") or "server"
        path = Path(value)
        return path if path.is_absolute() else (self.base_dir / path).resolve()

    @property
    def nsum_runtime(self) -> Path:
        value = self.raw.get("nsum_runtime") or "NeoServerUpdateModpack"
        path = Path(value)
        return path if path.is_absolute() else (self.base_dir / path).resolve()

    @property
    def java(self) -> str:
        return str(self.raw.get("java") or "java")

    @property
    def sync_format(self) -> str:
        return str(self.raw.get("sync_format") or "hmcl")

    @property
    def auto_install_core(self) -> bool:
        return bool(self.raw.get("auto_install_core", True))

    @property
    def launch_on_sync_failure(self) -> bool:
        return bool(self.raw.get("launch_on_sync_failure", False))

    @property
    def prepare_on_load(self) -> bool:
        return bool(self.raw.get("prepare_on_load", False))

    @property
    def timeout_seconds(self) -> int:
        return int(self.raw.get("timeout_seconds") or 1800)

    def save(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "config.json").write_text(
            json.dumps(self.raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def config_dir(server) -> Path:
    """MCDR 插件配置目录；脱离 MCDR 时回退到当前目录。"""
    try:
        return Path(server.get_data_folder()).parent  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        return Path.cwd()


def load_config(server=None) -> Config:
    base = config_dir(server)
    path = base / "config.json"
    raw = dict(DEFAULT_CONFIG)
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw.update(loaded)
        except Exception:  # noqa: BLE001
            pass
    if not raw.get("repo"):
        env = os.environ.get("NSUM_REPO", "")
        if env:
            raw["repo"] = env
    config = Config(base_dir=base, raw=raw)
    if not path.is_file():
        try:
            config.save()
        except Exception:  # noqa: BLE001
            pass
    return config
