"""MCDReforged 配置同步：核心/服务端变化时更新 `handler`（日志解析与命令输入方式）。"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

Log = Callable[[str], None]

# MCDR 的 handler 决定「如何解析服务端日志、如何向服务端输入命令」。
# 不同核心必须匹配不同 handler，否则控制台命令与日志事件都会失效。
HANDLER_BY_CORE = {
    "vanilla": "vanilla_handler",
    "paper": "bukkit_handler",
    "purpur": "bukkit_handler",
    "folia": "bukkit_handler",
    "spigot": "bukkit_handler",
    "pufferfish": "bukkit_handler",
    "fabric": "fabric_handler",
    "quilt": "fabric_handler",
    "forge": "forge_handler",
    "neoforge": "forge_handler",
    "mohist": "forge_handler",
    "arclight": "forge_handler",
    "cardboard": "fabric_handler",
    "velocity": "velocity_handler",
    "bungeecord": "bungeecord_handler",
    "waterfall": "bungeecord_handler",
    "geyser": "vanilla_handler",
}


def handler_for(core_id: str, modloader: str = "") -> str:
    core = (core_id or "").strip().lower()
    if core in HANDLER_BY_CORE:
        return HANDLER_BY_CORE[core]
    loader = (modloader or "").strip().lower()
    if loader in HANDLER_BY_CORE:
        return HANDLER_BY_CORE[loader]
    return "vanilla_handler"


def sync_handler(server, core_id: str, modloader: str = "", log: Log = print) -> Optional[str]:
    """把 MCDR 配置里的 handler 改成与当前核心匹配的值。

    返回实际写入的 handler；无法访问配置时返回 None（不阻断启动）。
    """
    wanted = handler_for(core_id, modloader)
    try:
        config = server.get_mcdr_config()
    except Exception:  # noqa: BLE001
        log("[NSUM] 无法读取 MCDR 配置，跳过 handler 同步")
        return None
    if not isinstance(config, dict):
        log("[NSUM] MCDR 配置格式异常，跳过 handler 同步")
        return None
    current = str(config.get("handler") or "")
    if current == wanted:
        return wanted
    config["handler"] = wanted
    save = getattr(server, "save_config", None)
    if callable(save):
        try:
            save()
            log(f"[NSUM] MCDR handler 已更新：{current or '(空)'} → {wanted}")
        except Exception as exc:  # noqa: BLE001
            log(f"[NSUM] 保存 MCDR 配置失败：{exc}")
            return None
    else:
        log(f"[NSUM] 已将 handler 设为 {wanted}（当前 MCDR 版本不支持自动保存，请手动确认）")
    return wanted
