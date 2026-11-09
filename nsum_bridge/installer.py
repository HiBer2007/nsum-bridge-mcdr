"""服务端核心 / 加载器安装与切换（全程无 GUI，只用命令行与 HTTP）。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from .instance import Instance, normalize_loader

Log = Callable[[str], None]

MOJANG_VERSION_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
FABRIC_INSTALLER = "https://maven.fabricmc.net/net/fabricmc/fabric-installer/{v}/fabric-installer-{v}.jar"
FABRIC_INSTALLER_VERSION = "1.0.1"
QUILT_INSTALLER = "https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/{v}/quilt-installer-{v}.jar"
QUILT_INSTALLER_VERSION = "0.11.1"
FORGE_MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge/{mc}-{ver}/forge-{mc}-{ver}-installer.jar"
NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge/{ver}/neoforge-{ver}-installer.jar"


def _download(url: str, target: Path, log: Log, sha1: str = "") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    log(f"[NSUM] 下载 {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if sha1:
        digest = hashlib.sha1(data).hexdigest()
        if digest.lower() != sha1.lower():
            raise RuntimeError(f"SHA1 校验失败：{url}")
    target.write_bytes(data)
    return target


def _run(cmd, cwd: Path, log: Log) -> None:
    log("[NSUM] 执行：" + " ".join(str(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").splitlines()[-15:])
        raise RuntimeError(f"命令失败（exit={proc.returncode}）：{tail}")


def _vanilla_server_url(mc_version: str) -> str:
    with urllib.request.urlopen(MOJANG_VERSION_MANIFEST, timeout=60) as response:
        manifest = json.loads(response.read().decode("utf-8"))
    for entry in manifest.get("versions", []):
        if entry.get("id") == mc_version:
            with urllib.request.urlopen(entry["url"], timeout=60) as response:
                detail = json.loads(response.read().decode("utf-8"))
            return detail["downloads"]["server"]["url"]
    raise RuntimeError(f"找不到 Minecraft 版本：{mc_version}")


def install_vanilla(instance: Instance, server_dir: Path, config, log: Log) -> None:
    url = _vanilla_server_url(instance.game_version)
    _download(url, server_dir / "server.jar", log)


def install_fabric(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = server_dir.parent / ".nsum" / "cache" / f"fabric-installer-{FABRIC_INSTALLER_VERSION}.jar"
    if not installer.is_file():
        _download(FABRIC_INSTALLER.format(v=FABRIC_INSTALLER_VERSION), installer, log)
    _run([config.java, "-jar", str(installer), "server",
          "-dir", str(server_dir), "-mcversion", instance.game_version,
          "-loader", instance.modloader_version, "-downloadMinecraft"], server_dir, log)


def install_quilt(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = server_dir.parent / ".nsum" / "cache" / f"quilt-installer-{QUILT_INSTALLER_VERSION}.jar"
    if not installer.is_file():
        _download(QUILT_INSTALLER.format(v=QUILT_INSTALLER_VERSION), installer, log)
    _run([config.java, "-jar", str(installer), "install", "server",
          instance.game_version, "--loader", instance.modloader_version,
          "--install-dir", str(server_dir), "--download-server"], server_dir, log)


def install_forge(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = server_dir.parent / ".nsum" / "cache" / "forge-installer.jar"
    url = FORGE_MAVEN.format(mc=instance.game_version, ver=instance.modloader_version)
    _download(url, installer, log)
    _run([config.java, "-jar", str(installer), "--installServer"], server_dir, log)


def install_neoforge(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = server_dir.parent / ".nsum" / "cache" / "neoforge-installer.jar"
    url = NEOFORGE_MAVEN.format(ver=instance.modloader_version)
    _download(url, installer, log)
    _run([config.java, "-jar", str(installer), "--installServer"], server_dir, log)


INSTALLERS = {
    "": install_vanilla,
    "vanilla": install_vanilla,
    "fabric": install_fabric,
    "quilt": install_quilt,
    "forge": install_forge,
    "neoforge": install_neoforge,
}


def ensure_core(instance: Instance, config, log: Log) -> bool:
    """确保服务端核心/加载器与三元组一致；返回是否发生了安装/切换。"""
    loader = normalize_loader(instance.modloader)
    installer = INSTALLERS.get(loader)
    if installer is None:
        raise RuntimeError(f"不支持的加载器：{instance.modloader}")

    if instance.matches() and _looks_installed(server_dir=config.server_dir, loader=loader):
        log(f"[NSUM] 核心/加载器已匹配（{instance.game_version} / {loader or 'vanilla'} "
            f"{instance.modloader_version}），跳过安装")
        return False

    if not instance.game_version:
        raise RuntimeError("实例缺少 gameVersion，无法安装服务端核心")

    log(f"[NSUM] 安装/切换服务端：{instance.game_version} / {loader or 'vanilla'} "
        f"{instance.modloader_version}")
    installer(instance, config.server_dir, config, log)
    instance.mark_installed()
    instance.write(config.server_dir)
    log("[NSUM] 服务端核心/加载器安装完成")
    return True


def _looks_installed(server_dir: Path, loader: str) -> bool:
    """轻量判断服务端是否已有可启动产物。"""
    server_dir = Path(server_dir)
    if loader == "fabric":
        return (server_dir / "fabric-server-launch.jar").is_file() or (server_dir / "fabric-server-launcher.jar").is_file()
    if loader == "quilt":
        return (server_dir / "quilt-server-launch.jar").is_file()
    if loader in ("forge", "neoforge"):
        return (server_dir / "libraries").is_dir() and any(server_dir.glob("run.*"))
    return (server_dir / "server.jar").is_file()
