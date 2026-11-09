"""插件目录同步：`plugins/`（jar）与 `plugin/<插件配置目录名>/`（插件配置）。

约定：
- 仓库 `plugins/` → 服务端 `plugins/`（插件 jar，按普通文件策略同步，Runtime 已处理）；
- 仓库 `plugin/<name>/…` → 服务端 `plugins/<name>/…`（插件配置，和 `/config` 一样支持子目录）；
  同步后删除中间目录 `plugin/`，避免服务端出现无意义目录。

不同插件的配置目录名不同，因此按 `<name>` 原样映射，不做白名单。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, List

Log = Callable[[str], None]

PLUGIN_CONFIG_SOURCE = "plugin"
PLUGINS_DIR = "plugins"


def apply_plugin_folders(server_dir: Path, log: Log = print) -> List[str]:
    """把 `plugin/<name>/` 合并进 `plugins/<name>/`，返回被处理的插件配置目录名。"""
    server_dir = Path(server_dir)
    source = server_dir / PLUGIN_CONFIG_SOURCE
    if not source.is_dir():
        return []
    target_root = server_dir / PLUGINS_DIR
    target_root.mkdir(parents=True, exist_ok=True)

    names: List[str] = []
    for child in sorted(source.iterdir()):
        if not child.is_dir():
            continue
        target = target_root / child.name
        target.mkdir(parents=True, exist_ok=True)
        _merge_tree(child, target)
        names.append(child.name)

    shutil.rmtree(source, ignore_errors=True)
    if names:
        log(f"[NSUM] 插件配置已映射到 plugins/：{', '.join(names)}")
    return names


def _merge_tree(source: Path, target: Path) -> None:
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            _merge_tree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)
