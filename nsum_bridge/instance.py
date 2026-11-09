"""实例标记：与 bridge（客户端）共用 `.NSUM/instance.json` 结构。

服务端额外字段：
- `branchType`: universal / client / server（服务端专用包才允许插件服核心）；
- `core` / `coreVersion`: 服务端核心（paper/folia/velocity/...）及其版本。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


INSTANCE_FILE = Path(".NSUM") / "instance.json"

BRANCH_UNIVERSAL = "universal"
BRANCH_CLIENT = "client"
BRANCH_SERVER = "server"


@dataclass
class Instance:
    repo: str = ""
    branch: str = "base"
    git_branch: str = ""
    branch_type: str = BRANCH_UNIVERSAL
    game_version: str = ""
    modloader: str = ""
    modloader_version: str = ""
    core: str = ""
    core_version: str = ""
    installed_game_version: str = ""
    installed_modloader: str = ""
    installed_loader_version: str = ""
    name: str = "NSUM"
    schema: int = 1

    @staticmethod
    def path(server_dir: Path) -> Path:
        return Path(server_dir) / INSTANCE_FILE

    @classmethod
    def read(cls, server_dir: Path) -> Optional["Instance"]:
        path = cls.path(server_dir)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
        return cls(
            repo=str(data.get("repo") or ""),
            branch=str(data.get("branch") or "base"),
            git_branch=str(data.get("gitBranch") or ""),
            branch_type=str(data.get("branchType") or BRANCH_UNIVERSAL),
            game_version=str(data.get("gameVersion") or ""),
            modloader=str(data.get("modloader") or ""),
            modloader_version=str(data.get("modloaderVersion") or ""),
            core=str(data.get("core") or ""),
            core_version=str(data.get("coreVersion") or ""),
            installed_game_version=str(data.get("installedGameVersion") or ""),
            installed_modloader=str(data.get("installedModloader") or ""),
            installed_loader_version=str(data.get("installedLoaderVersion") or ""),
            name=str(data.get("name") or "NSUM"),
            schema=int(data.get("schema") or 1),
        )

    def write(self, server_dir: Path) -> None:
        path = self.path(server_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema": self.schema,
            "repo": self.repo,
            "branch": self.branch,
            "gitBranch": self.git_branch,
            "branchType": self.branch_type,
            "name": self.name,
            "gameVersion": self.game_version,
            "modloader": self.modloader,
            "modloaderVersion": self.modloader_version,
            "core": self.core,
            "coreVersion": self.core_version,
            "installedGameVersion": self.installed_game_version,
            "installedModloader": self.installed_modloader,
            "installedLoaderVersion": self.installed_loader_version,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def is_client_only(self) -> bool:
        return normalize_branch_type(self.branch_type) == BRANCH_CLIENT

    @property
    def allows_plugin_servers(self) -> bool:
        return normalize_branch_type(self.branch_type) == BRANCH_SERVER

    def mark_installed(self) -> None:
        self.installed_game_version = self.game_version
        self.installed_modloader = normalize_loader(self.modloader)
        self.installed_loader_version = self.modloader_version

    def matches(self) -> bool:
        """三元组是否与已安装一致（空值视为未知，不阻断）。"""
        if not self.installed_game_version and not self.installed_modloader:
            return True
        if self.installed_game_version and self.installed_game_version != self.game_version:
            return False
        if self.installed_modloader and normalize_loader(self.installed_modloader) != normalize_loader(self.modloader):
            return False
        if self.installed_loader_version and self.installed_loader_version != self.modloader_version:
            return False
        return True


def normalize_branch_type(value: str) -> str:
    text = (value or "").strip().lower()
    aliases = {
        "generic": BRANCH_UNIVERSAL,
        "universal": BRANCH_UNIVERSAL,
        "both": BRANCH_UNIVERSAL,
        "client": BRANCH_CLIENT,
        "client_only": BRANCH_CLIENT,
        "clientonly": BRANCH_CLIENT,
        "server": BRANCH_SERVER,
        "server_only": BRANCH_SERVER,
        "serveronly": BRANCH_SERVER,
    }
    return aliases.get(text, BRANCH_UNIVERSAL)


def normalize_loader(value: str) -> str:
    text = (value or "").strip().lower()
    aliases = {
        "fabric-loader": "fabric",
        "fabricloader": "fabric",
        "quilt-loader": "quilt",
        "neo-forge": "neoforge",
        "forge-loader": "forge",
        "vanilla": "",
        "none": "",
    }
    return aliases.get(text, text)
