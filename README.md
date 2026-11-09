# NSUM Bridge (Server / MCDReforged)

服务端版的 NSUM 同步器：**在服务器启动之前**完成

1. 读取 `.NSUM/instance.json`（游戏版本 / 加载器 / 加载器版本 / 仓库 / 分支）；
2. 三元组（游戏版本、加载器、加载器版本）不一致时，自动安装或切换**服务端核心与加载器**；
3. 调用 NSUM Runtime CLI 同步整合包内容（mods/config/…，含指针下载、覆盖规则、serverconfig 规则）；
4. 任一步失败即报错并阻止启动（可在配置里允许同步失败仍启动）。

全程无 GUI，只用配置文件 + 日志，适合 **Linux 无桌面** 服务器。

## 安装

把本仓库放进 MCDR 的 `plugins/` 目录（或打包成 `.mcdr` 放入 `plugins/`），MCDR 会自动加载
`mcdreforged.plugin.json` 指定的入口 `nsum_bridge`。

依赖：MCDReforged >= 2.10；NSUM Runtime（`NeoServerUpdateModpack`）在 `nsum_runtime` 指定的路径；
Java 在 `java` 指定的路径或 PATH。

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
- `auto_install_core`：是否自动安装/切换服务端核心与加载器。
- `launch_on_sync_failure`：同步失败时是否仍允许启动（默认 false，即失败即中止）。
- `prepare_on_load`：MCDR 版本不支持 `on_server_start_pre` 时，可在加载阶段预同步。

实例标记示例（与客户端 bridge 共用格式）：

```json
{
  "schema": 1,
  "repo": "git@github.com:you/your-server-repo.git",
  "branch": "base",
  "gitBranch": "main",
  "name": "Server",
  "gameVersion": "1.21.1",
  "modloader": "fabric",
  "modloaderVersion": "0.16.9",
  "installedGameVersion": "1.21.1",
  "installedModloader": "fabric",
  "installedLoaderVersion": "0.16.9"
}
```

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

常用参数：`--no-core`（只同步内容）、`--allow-sync-failure`（同步失败仍返回 0）、
`--java /usr/bin/java`、`--config /etc/nsum/config.json`。

## 支持的加载器

| 加载器 | 安装方式 |
|---|---|
| 原版（空字符串） | 下载 Mojang `server.jar` |
| `fabric` | `fabric-installer server -mcversion … -loader … -downloadMinecraft` |
| `quilt` | `quilt-installer install server … --download-server` |
| `forge` | `forge-<mc>-<ver>-installer.jar --installServer` |
| `neoforge` | `neoforge-<ver>-installer.jar --installServer` |

切换判定：实例标记里的 `installed*` 三元组与 `gameVersion/modloader/modloaderVersion` 比较；
不一致或目标产物缺失时重新安装，成功后写回 `installed*`。

## 测试

离线单元测试（无需网络/MCDR/服务端）：

```bash
python -m unittest discover -s tests
```

已在 Windows 无 GUI 环境实测（同套代码适用于 Linux）：

- 内容同步：exit 0，`config/` 等按规则落地；
- Fabric 安装：生成 `fabric-server-launch.jar`、`libraries/`、`server.jar`；
- 加载器版本切换：0.16.9 → 0.15.11；
- 游戏版本切换：1.21.1 → 1.20.1（Fabric 0.15.11）。

## 注意

- MCDR 的 `on_server_start_pre` 在 2.12+ 提供；更早版本请使用 `prepare_on_load` 或上面的 CLI 包装脚本。
- 同步失败时插件会抛错并记录到 MCDR 日志；若需要「绝对不能启动」，用 CLI 包装脚本控制启动流程最可靠。
