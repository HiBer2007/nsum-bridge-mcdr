"""定位并暴露 **内置 Git**（NSUM 安装目录下的 tools/git），不依赖系统 Git。

布局（与 NSUM Runtime 的 install_config 一致）：
    <install>/tools/git/bin/git.exe            PortableGit
    <install>/tools/git/mingw64/bin/git.exe    MinGit
    <install>/tools/git/cmd/git.exe            MinGit

Runtime 所在目录的上一级也查（部署布局 build/deploy + build/tools/git）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def candidate_dirs(runtime_dir: Path) -> List[Path]:
    runtime = Path(runtime_dir)
    if runtime.is_file() or runtime.suffix.lower() == ".exe":
        roots = [runtime.parent, runtime.parent.parent]
    else:
        roots = [runtime, runtime.parent]
    dirs: List[Path] = []
    for root in roots:
        dirs.append(root / "tools" / "git")
    return dirs


def git_candidates(runtime_dir: Path) -> List[Path]:
    result: List[Path] = []
    for git_dir in candidate_dirs(runtime_dir):
        result.extend([
            git_dir / "bin" / "git.exe",
            git_dir / "mingw64" / "bin" / "git.exe",
            git_dir / "ucrt64" / "bin" / "git.exe",
            git_dir / "cmd" / "git.exe",
        ])
    return result


def _works(exe: Path) -> bool:
    try:
        proc = subprocess.run([str(exe), "--version"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=15)
        return proc.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def resolve_git(runtime_dir: Path, override: str = "") -> Optional[Path]:
    """返回可运行的内置 Git 路径；override 优先（允许手动指定）。"""
    if override:
        path = Path(override)
        if path.is_file() and _works(path):
            return path
        return None
    for candidate in git_candidates(runtime_dir):
        if candidate.is_file() and _works(candidate):
            return candidate
    found = shutil.which("git")
    if found:
        return Path(found)
    return None


def env_with_git(git_exe: Optional[Path], base: Optional[dict] = None) -> dict:
    """把 Git 所在目录放到 PATH 最前面（BuildTools 等外部工具靠 PATH 调 git）。"""
    env = dict(base if base is not None else os.environ)
    if git_exe is not None:
        env["PATH"] = str(Path(git_exe).parent) + os.pathsep + env.get("PATH", "")
    return env
