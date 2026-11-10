"""NSUM Bridge for MCDReforged.

在服务器启动之前完成：
1. 读取 `.NSUM/instance.json`（游戏版本 / 加载器 / 加载器版本 / 仓库 / 分支）；
2. 三元组不一致时安装或切换服务端核心与加载器（原版 / Fabric / Quilt / Forge / NeoForge）；
3. 调用 NSUM Runtime CLI 同步整合包内容（mods/config/...，含指针下载与覆盖规则）；
4. 任一步失败则中止启动（抛异常，MCDR 会记录错误；也可用 CLI 包装脚本让启动直接失败）。

无 GUI：全部通过配置文件 + MCDR 日志，适合 Linux 无桌面服务器。
"""

from __future__ import annotations

import os
from typing import Optional

from .config import load_config
from .instance import Instance
from .prepare import PrepareResult, prepare

PLUGIN_VERSION = "0.3.1"

_server = None
_logger = None


def _log(message: str):
    if _logger is not None:
        _logger.info(message)
    else:
        print(message, flush=True)


def on_load(server, old_module):
    global _server, _logger
    _server = server
    _logger = server.logger
    config = load_config(server)
    _log(f"[NSUM] NSUM Bridge (server) {PLUGIN_VERSION} 已加载；server_dir={config.server_dir}")
    if config.prepare_on_load:
        _log("[NSUM] 配置要求在加载时预同步…")
        try:
            result = prepare(config, log=_log, server=server)
            _log(f"[NSUM] 预同步完成：{result.summary()}")
        except Exception as exc:  # noqa: BLE001
            _log(f"[NSUM] 预同步失败：{exc}")


def on_server_start_pre(server):
    """服务器进程启动前执行（MCDR 2.12+）。失败时抛出异常阻止后续流程。"""
    config = load_config(server)
    if not config.enabled:
        server.logger.info("[NSUM] 已在配置中关闭，跳过启动前同步")
        return
    server.logger.info("[NSUM] 启动前同步开始…")
    result = prepare(config, log=server.logger.info, server=server)
    server.logger.info(f"[NSUM] 启动前同步完成：{result.summary()}")


def on_unload(server):
    server.logger.info("[NSUM] NSUM Bridge 已卸载")
