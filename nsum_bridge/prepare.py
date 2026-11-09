"""启动前准备流程：读实例 → 安装/切换核心 → 同步内容 → 同步 MCDR 配置。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from . import cores
from .config import Config
from .instance import Instance, normalize_branch_type
from .installer import ensure_core
from .mcdr_config import sync_handler
from .pluginsync import apply_plugin_folders
from .sync import sync

Log = Callable[[str], None]


@dataclass
class PrepareResult:
    instance: Optional[Instance] = None
    installed: bool = False
    synced: bool = False
    core: str = ""
    handler: str = ""
    plugin_folders: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [f"核心：{cores.describe(self.core) or '（未指定）'}"]
        parts.append("核心已切换" if self.installed else "核心无变化")
        parts.append("内容已同步" if self.synced else "内容未同步")
        if self.handler:
            parts.append(f"MCDR handler：{self.handler}")
        if self.plugin_folders:
            parts.append("插件配置：" + ", ".join(self.plugin_folders))
        if self.notes:
            parts.append("；".join(self.notes))
        return "，".join(parts)


def prepare(config: Config, log: Log = print, server=None) -> PrepareResult:
    """执行启动前准备；错误会抛出 RuntimeError（由调用方决定是否阻止启动）。"""
    server_dir = config.server_dir
    server_dir.mkdir(parents=True, exist_ok=True)

    instance = Instance.read(server_dir)
    if instance is None:
        if not config.repo:
            raise RuntimeError(
                f"{server_dir} 下没有 .NSUM/instance.json，且配置未提供 repo；"
                "请先放置实例标记或填写 repo/branch"
            )
        instance = Instance(repo=config.repo, branch=config.branch,
                            git_branch=config.git_branch, name="NSUM")
        log("[NSUM] 未找到实例标记，已按配置创建（仅同步，不安装核心）")
        instance.write(server_dir)
    else:
        if config.repo and not instance.repo:
            instance.repo = config.repo
            instance.branch = config.branch or instance.branch
            instance.write(server_dir)

    if instance.is_client_only:
        raise RuntimeError("该分支为「客户端专用」，不能用于服务端启动")

    core_id = (instance.core or "").strip().lower() or instance.modloader or "vanilla"
    result = PrepareResult(instance=instance, core=core_id)

    if config.auto_install_core and instance.game_version:
        result.installed = ensure_core(instance, config, log)
    elif config.auto_install_core:
        log("[NSUM] 实例未提供 gameVersion，跳过核心安装")

    if instance.repo:
        try:
            sync(config, log)
            result.synced = True
        except Exception as exc:  # noqa: BLE001
            if config.launch_on_sync_failure:
                log(f"[NSUM] 同步失败但配置允许继续启动：{exc}")
                result.notes.append("同步失败")
            else:
                raise
    else:
        log("[NSUM] 未配置仓库地址，跳过内容同步")
        result.notes.append("无仓库地址")

    result.plugin_folders = apply_plugin_folders(server_dir, log)

    if server is not None:
        handler = sync_handler(server, core_id, instance.modloader, log)
        if handler:
            result.handler = handler

    return result
