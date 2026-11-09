# NSUM Bridge (Server / MCDReforged)

服务端版的 NSUM 同步器：**在服务器启动之前**完成

1. 读取 `.NSUM/instance.json`（仓库 / 分支 / 分支类型 / 游戏版本 / 加载器或核心 / 版本）；
2. 核心或加载器不一致时，自动安装或切换**服务端核心**（原版 / 插件服 / 模组服 / 混合服 / 代理服 / 基岩互通）；
3. 调用 NSUM Runtime CLI 同步整合包内容（mods/config/…，含指针下载、覆盖规则、serverconfig 规则）；
4. 把仓库 `plugin/<插件配置目录>/` 映射到服务端 `plugins/<插件配置目录>/`（插件配置，和 `/config` 一样支持子目录）；
5. 按当前核心更新 **MCDReforged 的 `handler`**（决定日志解析方式与命令输入方式）；
6. 任一步失败即报错并阻止启动（可在配置里允许同步失败仍启动）。

全程无 GUI，只用配置文件 + 日志，适合 **Linux 无桌面** 服务器。

## 分支类型

分支属性 `type` 决定这个包能用在什么环境：

| `type` | 含义 | 服务端核心选择 |
|---|---|---|
| `universal` | 通用包 | 只能选模组服/原版核心 |
| `client` | 客户端专用 | **不能在服务端启动**（直接报错） |
| `server` | 服务端专用 | 可选全部核心，包含插件服 |

只有 `server` 分支允许插件服核心（Paper / Purpur / Folia / Spigot / Pufferfish 等）。

## 支持的核心

| 分类 | 核心 | 自动安装 |
|---|---|---|
| 原版 | Minecraft 官方服务端 | ✅ 下载 Mojang `server.jar` |
| 插件服 | Paper / Purpur / Folia | ✅ PaperMC API / Purpur API 下载 |
| 插件服 | Spigot / Pufferfish | ⚠️ 需手动放置（构建链复杂） |
| 模组服 | Fabric / Quilt / Forge / NeoForge | ✅ 官方安装器 |
| 混合服 | Mohist / Arclight / Cardboard | ⚠️ 需手动放置 |
| 代理服 | Velocity / Waterfall / BungeeCord | ✅ 下载最新构建 |
| 基岩互通 | Geyser（Standalone） | ✅ 下载最新构建 |

查看完整清单与分类：

```bash
python -m nsum_bridge.cli --list-cores
```

## MCDR handler 同步

不同核心的日志格式与命令输入方式不同，插件会按核心自动改写 MCDR `config.yml` 的 `handler`：

| 核心 | handler |
|---|---|
| vanilla / geyser | `vanilla_handler` |
| paper / purpur / folia / spigot / pufferfish | `bukkit_handler` |
| fabric / quilt / cardboard | `fabric_handler` |
| forge / neoforge / mohist / arclight | `forge_handler` |
| velocity | `velocity_handler` |
| bungeecord / waterfall | `bungeecord_handler` |

## 安装

把本仓库放进 MCDR 的 `plugins/` 目录（或打包成 `.mcdr` 放入 `plugins/`），MCDR 会自动加载
`mcdreforged.plugin.json` 指定的入口 `nsum_bridge`。

依赖：MCDReforged >= 2.10；NSUM Runtime（`NeoServerUpdateModpack`）在 `nsum_runtime` 指定的路径；
Java 在 `java` 指定的路径或 PATH。**不需要 FLFHMCL**。

## 配置

MCDR 插件配置目录下的 `config.json`（首次加载自动生成）：

```json
{
  "enabled": true,
  "repo": "git@github.com:you/your-server-repo.git",
  "branch": "base",
  "git_branch": "main",
  "server_dir": "server",
  "nsum_runtime": "NeoServerUpdateModpack",
  "java": "java",
  "sync_format": "hmcl",
  "auto_install_core": true,
  "launch_on_sync_failure": false,
  "prepare_on_load": false,
  "timeout_seconds": 1800
}
```

- `server_dir`：服务端工作目录（相对 MCDR 根目录或绝对路径），实例标记位于 `<server_dir>/.NSUM/instance.json`。
- `nsum_runtime`：NSUM Runtime 可执行文件（Linux 下为 `NeoServerUpdateModpack`）。
- `auto_install_core`：是否自动安装/切换服务端核心。
- `launch_on_sync_failure`：同步失败时是否仍允许启动（默认 false，即失败即中止）。
- `prepare_on_load`：MCDR 版本不支持 `on_server_start_pre` 时，可在加载阶段预同步。

实例标记示例（与客户端 bridge 共用格式，服务端多 `branchType` / `core` / `coreVersion`）：

```json
{
  "schema": 1,
  "repo": "git@github.com:you/your-server-repo.git",
  "branch": "base",
  "gitBranch": "main",
  "branchType": "server",
  "name": "Server",
  "gameVersion": "1.21.1",
  "modloader": "",
  "modloaderVersion": "",
  "core": "paper",
  "coreVersion": "",
  "installedGameVersion": "1.21.1",
  "installedModloader": "",
  "installedLoaderVersion": ""
}
```

## 插件目录与插件配置

- 仓库 `plugins/` → 服务端 `plugins/`：插件 jar，按普通文件策略同步（Runtime 处理）；
- 仓库 `plugin/<插件配置目录名>/…` → 服务端 `plugins/<插件配置目录名>/…`：插件配置，支持任意子目录；
  同步完成后删除中间目录 `plugin/`。不同插件的配置目录名不同，因此按目录名原样映射，不做白名单。

## 无 GUI 调试 / 启动脚本

不装 MCDR 也能直接跑同一套逻辑（推荐在启动脚本里先执行，失败则不启动 MCDR）：

```bash
python -m nsum_bridge.cli \
  --repo git@github.com:you/your-server-repo.git \
  --branch base --git-branch main \
  --server-dir /srv/mc \
  --runtime /opt/nsum/NeoServerUpdateModpack
```

退出码：`0` 成功；`1` 准备失败（应阻止启动）；`2` 参数错误。

常用参数：`--no-core`（只同步内容）、`--allow-sync-failure`、`--java /usr/bin/java`、
`--config /etc/nsum/config.json`、`--list-cores`。

## 测试

离线单元测试（无需网络/MCDR/服务端）：

```bash
python -m unittest discover -s tests
```

实测（Windows 无 GUI，同套代码适用于 Linux）：单元测试 15/15；内容同步 exit=0；
Fabric 安装；加载器版本 0.16.9→0.15.11；游戏版本 1.21.1→1.20.1。

## 注意

- MCDR 的 `on_server_start_pre` 在 2.12+ 提供；更早版本请使用 `prepare_on_load` 或上面的 CLI 包装脚本。
- 同步失败时插件会抛错并记录到 MCDR 日志；若需要「绝对不能启动」，用 CLI 包装脚本控制启动流程最可靠。
- 插件服核心只在 `branchType=server` 时允许；客户端专用分支会被直接拒绝。
