"""服务端核心目录（分类 + 下载与安装方式 + MCDR handler 映射）。

分类：
- vanilla  原版
- plugin   插件服（Bukkit 系）
- modded   模组服（Fabric / Quilt / Forge / NeoForge）
- hybrid   混合服（插件 + 模组）
- proxy    代理服（Velocity / BungeeCord / Waterfall）
- geyser   基岩版互通（Geyser）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

CATEGORY_LABELS = {
    "vanilla": "原版",
    "plugin": "插件服",
    "modded": "模组服",
    "hybrid": "混合服",
    "proxy": "代理服",
    "geyser": "基岩版互通",
}


@dataclass(frozen=True)
class Core:
    id: str
    name: str
    category: str
    handler: str          # MCDR config.yml 的 handler
    installer: str        # 安装方式标识，见 installer.py
    supports_plugins: bool = False


CORES: List[Core] = [
    # 原版
    Core("vanilla", "Minecraft 原版（官方服务端）", "vanilla", "vanilla_handler", "vanilla"),
    # 插件服
    Core("paper", "Paper", "plugin", "bukkit_handler", "paper", True),
    Core("purpur", "Purpur", "plugin", "bukkit_handler", "purpur", True),
    Core("folia", "Folia（多线程）", "plugin", "bukkit_handler", "folia", True),
    Core("spigot", "Spigot", "plugin", "bukkit_handler", "spigot", True),
    Core("pufferfish", "Pufferfish", "plugin", "bukkit_handler", "pufferfish", True),
    # 模组服
    Core("fabric", "Fabric", "modded", "fabric_handler", "fabric"),
    Core("quilt", "Quilt", "modded", "fabric_handler", "quilt"),
    Core("forge", "Forge", "modded", "forge_handler", "forge"),
    Core("neoforge", "NeoForge", "modded", "forge_handler", "neoforge"),
    # 混合服
    Core("mohist", "Mohist（Forge + Bukkit）", "hybrid", "forge_handler", "mohist", True),
    Core("arclight", "Arclight（Forge/NeoForge + Bukkit）", "hybrid", "forge_handler", "arclight", True),
    Core("cardboard", "Cardboard（Fabric + Bukkit）", "hybrid", "fabric_handler", "cardboard", True),
    # 代理服
    Core("velocity", "Velocity", "proxy", "velocity_handler", "velocity"),
    Core("bungeecord", "BungeeCord", "proxy", "bungeecord_handler", "bungeecord"),
    Core("waterfall", "Waterfall", "proxy", "bungeecord_handler", "waterfall"),
    # 基岩版互通
    Core("geyser", "Geyser（基岩版 Java 互通）", "geyser", "vanilla_handler", "geyser"),
]

_BY_ID: Dict[str, Core] = {core.id: core for core in CORES}


def get(core_id: str) -> Optional[Core]:
    return _BY_ID.get((core_id or "").strip().lower())


def by_category() -> Dict[str, List[Core]]:
    result: Dict[str, List[Core]] = {}
    for core in CORES:
        result.setdefault(core.category, []).append(core)
    return result


def categories() -> List[str]:
    return [c for c in CATEGORY_LABELS if c in by_category()]


def describe(core_id: str) -> str:
    core = get(core_id)
    if core is None:
        return core_id or "（未指定）"
    return f"{CATEGORY_LABELS.get(core.category, core.category)} / {core.name}"


def supports_plugins(core_id: str) -> bool:
    core = get(core_id)
    return bool(core and core.supports_plugins)
