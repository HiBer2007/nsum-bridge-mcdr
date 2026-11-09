"""启动前准备流程：读实例 → 安装/切换核心 → 同步内容。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .config import Config
from .instance import Instance
from .installer import ensure_core
from .sync import sync

Log = Callable[[str], None]


@dataclass
class PrepareResult:
    instance: Optional[Instance] = None
    installed: bool = False
    synced: bool = False
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = []
        parts.append("核心已切换" if self.installed else "核心无变化")
        parts.append("内容已同步" if self.synced else "内容未同步")
        if self.notes:
            parts.append("；".join(self.notes))
        return "，".join(parts)


def prepare(config: Config, log: Log = print) -> PrepareResult:
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

    result = PrepareResult(instance=instance)

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

    return result
