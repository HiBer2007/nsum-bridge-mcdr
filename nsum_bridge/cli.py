"""无 GUI 命令行入口：适合 Linux 服务器启动脚本在拉起 MCDR/服务端之前调用。

用法：
    python -m nsum_bridge.cli --repo <url> --server-dir /srv/mc --branch base
    python -m nsum_bridge.cli --config /etc/nsum/config.json

退出码：0 = 成功；1 = 准备失败（应阻止启动）；2 = 参数错误。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config, DEFAULT_CONFIG
from . import cores
from .prepare import prepare


def build_config(args) -> Config:
    base = Path(args.config).resolve() if args.config else Path.cwd()
    if args.config:
        raw = dict(DEFAULT_CONFIG)
        raw.update(json.loads(Path(args.config).read_text(encoding="utf-8")))
        return Config(base_dir=base, raw=raw)
    return Config(base_dir=Path.cwd(), raw={
        **DEFAULT_CONFIG,
        "repo": args.repo or "",
        "branch": args.branch,
        "git_branch": args.git_branch,
        "server_dir": args.server_dir or "server",
        "nsum_runtime": args.runtime or "NeoServerUpdateModpack",
        "java": args.java,
        "auto_install_core": not args.no_core,
        "launch_on_sync_failure": args.allow_sync_failure,
    })


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="nsum_bridge")
    parser.add_argument("--config", help="配置文件路径（JSON）")
    parser.add_argument("--repo", help="NSUM 仓库地址")
    parser.add_argument("--branch", default="base", help="整合包分支")
    parser.add_argument("--git-branch", default="", help="git 分支")
    parser.add_argument("--server-dir", help="服务端目录（默认 ./server）")
    parser.add_argument("--runtime", help="NSUM Runtime 可执行文件路径")
    parser.add_argument("--java", default="java", help="Java 可执行文件")
    parser.add_argument("--no-core", action="store_true", help="不安装/切换服务端核心")
    parser.add_argument("--allow-sync-failure", action="store_true", help="同步失败仍返回 0")
    parser.add_argument("--list-cores", action="store_true", help="列出全部服务端核心（按分类）")
    args = parser.parse_args(argv)

    if args.list_cores:
        for category in cores.categories():
            print(f"[{cores.CATEGORY_LABELS[category]}]")
            for core in cores.by_category()[category]:
                mark = " (支持插件)" if core.supports_plugins else ""
                print(f"  {core.id:<10} {core.name}{mark}  handler={core.handler}")
        return 0

    if not args.config and not args.repo:
        parser.print_help()
        return 2

    config = build_config(args)
    try:
        result = prepare(config, log=lambda m: print(m, flush=True))
    except Exception as exc:  # noqa: BLE001
        print(f"[NSUM] 准备失败：{exc}", file=sys.stderr, flush=True)
        return 0 if args.allow_sync_failure else 1
    print(f"[NSUM] 准备完成：{result.summary()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
