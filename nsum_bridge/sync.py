"""调用 NSUM Runtime CLI 同步整合包内容（无 GUI，逐行解析进度）。"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

STEP_RE = re.compile(r"\[([A-Za-z_]+)\s+(\d+)%\]\s*(.*)")
BAR_RE = re.compile(r"(\d+)%\s*\|\s*([^\[]*)")

Log = Callable[[str], None]


def build_command(runtime: Path, repo: str, branch: str, git_branch: str,
                  server_dir: Path, sync_format: str = "hmcl") -> List[str]:
    cmd = [str(runtime), "exec", "build", "--repo", repo, "--modpack", branch]
    if git_branch:
        cmd += ["--git-branch", git_branch]
    cmd += ["--format", sync_format, "--export", str(server_dir)]
    return cmd


def describe_stage(stage: str) -> str:
    return {
        "clone": "拉取仓库",
        "checkout": "切换分支",
        "merge": "合并分支",
        "process_files": "处理文件",
        "pointer": "下载指针文件",
        "config": "同步配置",
        "custom_mods": "处理自定义模组",
        "finalize": "生成版本文件",
        "server_config": "同步存档配置",
        "download": "下载",
        "done": "完成",
    }.get(stage, stage)


@dataclass
class SyncResult:
    returncode: int
    lines: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def sync(config, log: Log = print) -> SyncResult:
    """执行同步；失败时抛出 RuntimeError（由调用方决定是否继续启动）。"""
    server_dir = config.server_dir
    server_dir.mkdir(parents=True, exist_ok=True)
    runtime = config.nsum_runtime
    if not Path(runtime).is_file():
        raise RuntimeError(f"NSUM Runtime 不存在：{runtime}")

    cmd = build_command(Path(runtime), config.repo, config.branch,
                        config.git_branch, server_dir, config.sync_format)
    log("[NSUM] 同步命令：" + " ".join(cmd))

    lines: List[str] = []
    process = subprocess.Popen(
        cmd,
        cwd=str(server_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        lines.append(line)
        step = STEP_RE.search(line)
        bar = BAR_RE.search(line)
        if step:
            log(f"[NSUM] {describe_stage(step.group(1))} {step.group(2)}% {step.group(3).strip()}")
        elif bar:
            log(f"[NSUM] {bar.group(1)}% {bar.group(2).strip()}")
        else:
            log("[NSUM] " + line)
    code = process.wait(timeout=None)
    if code != 0:
        tail = "\n".join(lines[-15:])
        raise RuntimeError(f"NSUM 同步失败（exit={code}）：\n{tail}")
    log("[NSUM] 同步完成")
    return SyncResult(returncode=code, lines=lines)
