"""服务端核心 / 加载器安装与切换（全程无 GUI，只用命令行与 HTTP）。

两类：
- 模组服（fabric/quilt/forge/neoforge）与原版：走官方安装器 / Mojang；
- 插件服与代理服（paper/folia/purpur/velocity/waterfall/bungeecord/geyser）：直接下载核心 jar 到 `server.jar`。
- 暂不自动安装（需手动放置）：spigot/pufferfish/mohist/arclight/cardboard —— 会给出明确错误。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from . import cores
from .instance import Instance, normalize_loader

Log = Callable[[str], None]

MOJANG_VERSION_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
PAPER_API = "https://api.papermc.io/v2/projects/{project}"
PURPUR_API = "https://api.purpurmc.org/v2/purpur/{mc}/latest/download"
BUNGEECORD = "https://ci.md-5.net/job/BungeeCord/lastSuccessfulBuild/artifact/bootstrap/target/BungeeCord.jar"
GEYSER_STANDALONE = ("https://download.geysermc.org/v2/projects/geyser/versions/latest/"
                     "builds/latest/downloads/standalone")
FABRIC_INSTALLER = "https://maven.fabricmc.net/net/fabricmc/fabric-installer/{v}/fabric-installer-{v}.jar"
FABRIC_INSTALLER_VERSION = "1.0.1"
QUILT_INSTALLER = ("https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/"
                   "{v}/quilt-installer-{v}.jar")
QUILT_INSTALLER_VERSION = "0.11.1"
FORGE_MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge/{mc}-{ver}/forge-{mc}-{ver}-installer.jar"
NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge/{ver}/neoforge-{ver}-installer.jar"

MANUAL_CORES: set = set()


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def _download(url: str, target: Path, log: Log, sha1: str = "") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    log(f"[NSUM] 下载 {url}")
    with urllib.request.urlopen(url, timeout=180) as response:
        data = response.read()
    if sha1 and hashlib.sha1(data).hexdigest().lower() != sha1.lower():
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


def _write_eula(server_dir: Path, log: Log) -> None:
    path = server_dir / "eula.txt"
    if path.is_file():
        return
    path.write_text("eula=true\n", encoding="utf-8")
    log("[NSUM] 已写入 eula.txt（eula=true）")


# --------------------------------------------------------------------------- 模组服 / 原版

def _vanilla_server_url(mc_version: str) -> str:
    manifest = _get_json(MOJANG_VERSION_MANIFEST)
    for entry in manifest.get("versions", []):
        if entry.get("id") == mc_version:
            detail = _get_json(entry["url"])
            return detail["downloads"]["server"]["url"]
    raise RuntimeError(f"找不到 Minecraft 版本：{mc_version}")


def install_vanilla(instance: Instance, server_dir: Path, config, log: Log) -> None:
    _download(_vanilla_server_url(instance.game_version), server_dir / "server.jar", log)
    _write_eula(server_dir, log)


def _installer_cache(server_dir: Path) -> Path:
    cache = server_dir.parent / ".nsum" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def install_fabric(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = _installer_cache(server_dir) / f"fabric-installer-{FABRIC_INSTALLER_VERSION}.jar"
    if not installer.is_file():
        _download(FABRIC_INSTALLER.format(v=FABRIC_INSTALLER_VERSION), installer, log)
    _run([config.java, "-jar", str(installer), "server",
          "-dir", str(server_dir), "-mcversion", instance.game_version,
          "-loader", instance.modloader_version, "-downloadMinecraft"], server_dir, log)
    _write_eula(server_dir, log)


def install_quilt(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = _installer_cache(server_dir) / f"quilt-installer-{QUILT_INSTALLER_VERSION}.jar"
    if not installer.is_file():
        _download(QUILT_INSTALLER.format(v=QUILT_INSTALLER_VERSION), installer, log)
    _run([config.java, "-jar", str(installer), "install", "server",
          instance.game_version, "--loader", instance.modloader_version,
          "--install-dir", str(server_dir), "--download-server"], server_dir, log)
    _write_eula(server_dir, log)


def install_forge(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = _installer_cache(server_dir) / "forge-installer.jar"
    _download(FORGE_MAVEN.format(mc=instance.game_version, ver=instance.modloader_version), installer, log)
    _run([config.java, "-jar", str(installer), "--installServer"], server_dir, log)
    _write_eula(server_dir, log)


def install_neoforge(instance: Instance, server_dir: Path, config, log: Log) -> None:
    installer = _installer_cache(server_dir) / "neoforge-installer.jar"
    _download(NEOFORGE_MAVEN.format(ver=instance.modloader_version), installer, log)
    _run([config.java, "-jar", str(installer), "--installServer"], server_dir, log)
    _write_eula(server_dir, log)


# --------------------------------------------------------------------------- 插件服 / 代理服

def install_paper(instance: Instance, server_dir: Path, config, log: Log, project: str = "paper") -> None:
    versions = _get_json(PAPER_API.format(project=project) + "/versions").get("versions", [])
    mc = instance.game_version
    if mc not in versions:
        raise RuntimeError(f"{project} 不支持 Minecraft {mc}（可选：{', '.join(versions[-6:])}）")
    builds = _get_json(f"{PAPER_API.format(project=project)}/versions/{mc}/builds").get("builds", [])
    if not builds:
        raise RuntimeError(f"{project} {mc} 没有可用构建")
    build = builds[-1]["build"]
    url = (f"{PAPER_API.format(project=project)}/versions/{mc}/builds/{build}/downloads/"
           f"{project}-{mc}-{build}.jar")
    _download(url, server_dir / "server.jar", log)
    _write_eula(server_dir, log)


def install_folia(instance: Instance, server_dir: Path, config, log: Log) -> None:
    install_paper(instance, server_dir, config, log, project="folia")


def install_purpur(instance: Instance, server_dir: Path, config, log: Log) -> None:
    _download(PURPUR_API.format(mc=instance.game_version), server_dir / "server.jar", log)
    _write_eula(server_dir, log)


def _paper_latest(project: str, log: Log) -> str:
    versions = _get_json(PAPER_API.format(project=project) + "/versions").get("versions", [])
    if not versions:
        raise RuntimeError(f"{project} 没有可用版本")
    version = versions[-1]
    builds = _get_json(f"{PAPER_API.format(project=project)}/versions/{version}/builds").get("builds", [])
    if not builds:
        raise RuntimeError(f"{project} {version} 没有可用构建")
    build = builds[-1]["build"]
    return (f"{PAPER_API.format(project=project)}/versions/{version}/builds/{build}/downloads/"
            f"{project}-{version}-{build}.jar")


def install_velocity(instance: Instance, server_dir: Path, config, log: Log) -> None:
    _download(_paper_latest("velocity", log), server_dir / "server.jar", log)


def install_waterfall(instance: Instance, server_dir: Path, config, log: Log) -> None:
    _download(_paper_latest("waterfall", log), server_dir / "server.jar", log)


def install_bungeecord(instance: Instance, server_dir: Path, config, log: Log) -> None:
    _download(BUNGEECORD, server_dir / "server.jar", log)


def install_geyser(instance: Instance, server_dir: Path, config, log: Log) -> None:
    _download(GEYSER_STANDALONE, server_dir / "server.jar", log)


# --------------------------------------------------------------------------- 其余插件服 / 混合服

GITHUB_RELEASES = "https://api.github.com/repos/{repo}/releases"
GITHUB_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
BUILDTOOLS = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"


def _github_assets(repo: str, limit: int = 30):
    """返回 [(tag, name, url)]，按发布时间从新到旧。"""
    releases = _get_json(GITHUB_RELEASES.format(repo=repo) + f"?per_page={limit}")
    result = []
    for release in releases:
        tag = str(release.get("tag_name") or "")
        for asset in release.get("assets", []):
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            if name and url:
                result.append((tag, name, url))
    return result


def _pick_asset(assets, mc_version: str, keywords) -> str:
    """从 GitHub 资产里挑出匹配 MC 版本与关键字的一个。"""
    lowered = [(tag, name, url) for tag, name, url in assets if name.lower().endswith(".jar")]
    for tag, name, url in lowered:
        text = f"{tag} {name}".lower()
        if mc_version and mc_version not in text:
            continue
        if not any(keyword in text for keyword in keywords):
            continue
        if any(bad in text for bad in ("sources", "javadoc", "installer", "api")):
            continue
        return url
    raise RuntimeError(f"没有找到匹配 {mc_version} 的构建（{', '.join(keywords)}）")


def install_spigot(instance: Instance, server_dir: Path, config, log: Log) -> None:
    """Spigot 需要 BuildTools 现编（依赖 git + JDK），全自动执行。"""
    cache = _installer_cache(server_dir)
    buildtools = cache / "BuildTools.jar"
    if not buildtools.is_file():
        _download(BUILDTOOLS, buildtools, log)
    _run([config.java, "-jar", str(buildtools), "--rev", instance.game_version,
          "--compile", "spigot"], cache, log)
    produced = sorted(cache.glob(f"spigot-{instance.game_version}*.jar"))
    if not produced:
        produced = sorted(cache.glob("spigot-*.jar"))
    if not produced:
        raise RuntimeError("BuildTools 未生成 spigot jar，请检查 git/JDK 与网络")
    (server_dir / "server.jar").write_bytes(produced[-1].read_bytes())
    _write_eula(server_dir, log)


def install_pufferfish(instance: Instance, server_dir: Path, config, log: Log) -> None:
    job = f"Pufferfish-{instance.game_version}"
    info = _get_json(f"https://ci.pufferfish.host/job/{job}/lastSuccessfulBuild/api/json")
    artifacts = info.get("artifacts") or []
    if not artifacts:
        raise RuntimeError(f"Pufferfish {instance.game_version} 没有可用构建")
    relative = artifacts[0]["relativePath"]
    _download(f"https://ci.pufferfish.host/job/{job}/lastSuccessfulBuild/artifact/{relative}",
              server_dir / "server.jar", log)
    _write_eula(server_dir, log)


def install_mohist(instance: Instance, server_dir: Path, config, log: Log) -> None:
    url = None
    try:
        builds = _get_json(f"https://mohistmc.com/api/v2/projects/mohist/{instance.game_version}/builds")
        entries = builds if isinstance(builds, list) else builds.get("builds", [])
        if entries:
            latest = entries[-1]
            url = latest.get("downloadUrl") or latest.get("download") or latest.get("url")
    except Exception:  # noqa: BLE001
        url = None
    if not url:
        url = _pick_asset(_github_assets("MohistMC/Mohist"), instance.game_version, ("mohist", "server"))
    _download(url, server_dir / "server.jar", log)
    _write_eula(server_dir, log)


def install_arclight(instance: Instance, server_dir: Path, config, log: Log) -> None:
    loader = (instance.modloader or "forge").lower()
    url = _pick_asset(_github_assets("IzzelAliz/Arclight"), instance.game_version, ("arclight", loader))
    _download(url, server_dir / "server.jar", log)
    _write_eula(server_dir, log)


def install_cardboard(instance: Instance, server_dir: Path, config, log: Log) -> None:
    try:
        url = _pick_asset(_github_assets("CardboardPowered/cardboard"), instance.game_version,
                          ("cardboard",))
    except Exception:  # noqa: BLE001
        latest = _get_json(GITHUB_LATEST.format(repo="CardboardPowered/cardboard"))
        assets = [(str(latest.get("tag_name") or ""), str(a.get("name") or ""),
                   str(a.get("browser_download_url") or "")) for a in latest.get("assets", [])]
        url = _pick_asset(assets, instance.game_version, ("cardboard",))
    _download(url, server_dir / "server.jar", log)
    _write_eula(server_dir, log)


# --------------------------------------------------------------------------- 路由

CORE_INSTALLERS = {
    "vanilla": install_vanilla,
    "fabric": install_fabric,
    "quilt": install_quilt,
    "forge": install_forge,
    "neoforge": install_neoforge,
    "paper": install_paper,
    "folia": install_folia,
    "purpur": install_purpur,
    "spigot": install_spigot,
    "pufferfish": install_pufferfish,
    "mohist": install_mohist,
    "arclight": install_arclight,
    "cardboard": install_cardboard,
    "velocity": install_velocity,
    "waterfall": install_waterfall,
    "bungeecord": install_bungeecord,
    "geyser": install_geyser,
}

LEGACY_INSTALLERS = {
    "": install_vanilla,
    "vanilla": install_vanilla,
    "fabric": install_fabric,
    "quilt": install_quilt,
    "forge": install_forge,
    "neoforge": install_neoforge,
}


def ensure_core(instance: Instance, config, log: Log) -> bool:
    """确保服务端核心/加载器与实例三元组一致；返回是否发生了安装/切换。"""
    if instance.is_client_only:
        raise RuntimeError("该分支为「客户端专用」，不能用于服务端")

    core_id = (instance.core or "").strip().lower()
    loader = normalize_loader(instance.modloader)
    if not core_id:
        core_id = loader or "vanilla"
    core = cores.get(core_id)
    if core is None:
        raise RuntimeError(f"未知的核心：{instance.core}")

    if core.supports_plugins and not instance.allows_plugin_servers:
        raise RuntimeError(
            f"核心 {core.name} 属于插件服，仅「服务端专用」分支可用；"
            f"当前分支类型为 {instance.branch_type}"
        )
    if core_id in MANUAL_CORES:
        raise RuntimeError(f"{core.name} 暂不支持自动安装，请手动放置服务端文件")
    installer = CORE_INSTALLERS.get(core_id)
    if installer is None:
        raise RuntimeError(f"核心 {core.name} 暂不支持自动安装")

    if instance.matches() and instance.installed_game_version and _looks_installed(config.server_dir, core_id):
        log(f"[NSUM] 核心已匹配（{instance.game_version} / {core.name}），跳过安装")
        return False

    if not instance.game_version:
        raise RuntimeError("实例缺少 gameVersion，无法安装服务端核心")

    log(f"[NSUM] 安装/切换服务端：{instance.game_version} / {core.name}")
    installer(instance, config.server_dir, config, log)
    instance.mark_installed()
    instance.write(config.server_dir)
    log("[NSUM] 服务端核心/加载器安装完成")
    return True


def _looks_installed(server_dir: Path, core_id: str) -> bool:
    server_dir = Path(server_dir)
    if core_id in ("fabric",):
        return (server_dir / "fabric-server-launch.jar").is_file()
    if core_id == "quilt":
        return (server_dir / "quilt-server-launch.jar").is_file()
    if core_id in ("forge", "neoforge"):
        return (server_dir / "libraries").is_dir() and any(server_dir.glob("run.*"))
    return (server_dir / "server.jar").is_file()
