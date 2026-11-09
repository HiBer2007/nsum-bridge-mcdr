import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nsum_bridge import cores
from nsum_bridge.config import Config, DEFAULT_CONFIG
from nsum_bridge.instance import Instance, normalize_branch_type, normalize_loader
from nsum_bridge.mcdr_config import handler_for
from nsum_bridge.pluginsync import apply_plugin_folders
from nsum_bridge.prepare import prepare
from nsum_bridge.sync import build_command, describe_stage
from nsum_bridge.installer import CORE_INSTALLERS, _looks_installed, _pick_asset


class InstanceTests(unittest.TestCase):
    def test_normalize_loader(self):
        self.assertEqual(normalize_loader("Fabric-Loader"), "fabric")
        self.assertEqual(normalize_loader("neo-forge"), "neoforge")
        self.assertEqual(normalize_loader("vanilla"), "")

    def test_branch_type(self):
        self.assertEqual(normalize_branch_type("server_only"), "server")
        self.assertEqual(normalize_branch_type("Client"), "client")
        self.assertEqual(normalize_branch_type(""), "universal")

    def test_matches(self):
        inst = Instance(game_version="1.21.1", modloader="fabric", modloader_version="0.16.9",
                        installed_game_version="1.21.1", installed_modloader="fabric",
                        installed_loader_version="0.16.9")
        self.assertTrue(inst.matches())
        inst.installed_loader_version = "0.15.11"
        self.assertFalse(inst.matches())

    def test_roundtrip_with_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inst = Instance(repo="r", branch="base", branch_type="server",
                            game_version="1.21.1", core="paper", core_version="123",
                            installed_game_version="1.21.1")
            inst.write(root)
            back = Instance.read(root)
            self.assertEqual(back.branch_type, "server")
            self.assertEqual(back.core, "paper")
            self.assertTrue(back.allows_plugin_servers)
            self.assertFalse(back.is_client_only)


class CoreCatalogTests(unittest.TestCase):
    def test_categories_cover_all(self):
        by_category = cores.by_category()
        self.assertIn("vanilla", by_category)
        self.assertIn("plugin", by_category)
        self.assertIn("hybrid", by_category)
        self.assertIn("proxy", by_category)
        self.assertTrue(all(c.category in by_category for c in cores.CORES))

    def test_supports_plugins(self):
        self.assertTrue(cores.supports_plugins("paper"))
        self.assertTrue(cores.supports_plugins("folia"))
        self.assertFalse(cores.supports_plugins("fabric"))
        self.assertFalse(cores.supports_plugins("velocity"))

    def test_describe(self):
        self.assertIn("Paper", cores.describe("paper"))


class HandlerTests(unittest.TestCase):
    def test_handler_mapping(self):
        self.assertEqual(handler_for("paper"), "bukkit_handler")
        self.assertEqual(handler_for("folia"), "bukkit_handler")
        self.assertEqual(handler_for("velocity"), "velocity_handler")
        self.assertEqual(handler_for("bungeecord"), "bungeecord_handler")
        self.assertEqual(handler_for("neoforge"), "forge_handler")
        self.assertEqual(handler_for("fabric"), "fabric_handler")
        self.assertEqual(handler_for("vanilla"), "vanilla_handler")
        self.assertEqual(handler_for("unknown", "fabric"), "fabric_handler")


class PluginFolderTests(unittest.TestCase):
    def test_maps_plugin_config_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = root / "plugin" / "EssentialsX" / "config.yml"
            cfg.parent.mkdir(parents=True)
            cfg.write_text("x: 1", encoding="utf-8")
            names = apply_plugin_folders(root, log=lambda m: None)
            self.assertEqual(names, ["EssentialsX"])
            self.assertTrue((root / "plugins" / "EssentialsX" / "config.yml").is_file())
            self.assertFalse((root / "plugin").exists())

    def test_no_plugin_folder_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(apply_plugin_folders(Path(tmp), log=lambda m: None), [])


class AssetPickTests(unittest.TestCase):
    def test_pick_asset_filters_sources_and_matches_mc(self):
        assets = [
            ("1.21.1-1.0", "arclight-forge-1.21.1-1.0.4.jar", "http://a"),
            ("1.21.1-1.0", "arclight-forge-1.21.1-1.0.4-sources.jar", "http://b"),
            ("1.20.1-1.0", "arclight-forge-1.20.1-1.0.0.jar", "http://c"),
        ]
        self.assertEqual(_pick_asset(assets, "1.21.1", ("arclight", "forge")), "http://a")
        with self.assertRaises(RuntimeError):
            _pick_asset(assets, "1.19.2", ("arclight", "forge"))

    def test_every_core_has_installer(self):
        for core in cores.CORES:
            self.assertIn(core.id, CORE_INSTALLERS)

class SyncAndInstallTests(unittest.TestCase):
    def test_build_command(self):
        runtime = Path(tempfile.mkdtemp()) / "NeoServerUpdateModpack"
        server = Path(tempfile.mkdtemp()) / "mc"
        cmd = build_command(runtime, "git@x/y.git", "base", "main", server)
        self.assertEqual(cmd[:4], [str(runtime), "exec", "build", "--repo"])
        self.assertEqual(cmd[-4:], ["--format", "hmcl", "--export", str(server)])

    def test_looks_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(_looks_installed(root, "paper"))
            (root / "server.jar").write_bytes(b"x")
            self.assertTrue(_looks_installed(root, "paper"))


class PrepareTests(unittest.TestCase):
    def _config(self, tmp, repo="git@x/y.git"):
        raw = dict(DEFAULT_CONFIG)
        raw.update({"repo": repo, "server_dir": "server"})
        return Config(base_dir=Path(tmp), raw=raw)

    def test_client_only_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(tmp)
            Instance(repo=cfg.repo, branch_type="client").write(cfg.server_dir)
            with self.assertRaises(RuntimeError):
                prepare(cfg, log=lambda m: None)

    def test_plugin_server_requires_server_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(tmp)
            Instance(repo=cfg.repo, branch_type="universal", game_version="1.21.1",
                     core="paper", modloader="").write(cfg.server_dir)
            with mock.patch("nsum_bridge.prepare.sync", return_value=None):
                with self.assertRaises(RuntimeError):
                    prepare(cfg, log=lambda m: None)

    def test_prepare_syncs_and_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(tmp)
            Instance(repo=cfg.repo, branch_type="server", game_version="1.21.1",
                     modloader="fabric", modloader_version="0.16.9").write(cfg.server_dir)
            with mock.patch("nsum_bridge.prepare.ensure_core", return_value=True) as core, \
                 mock.patch("nsum_bridge.prepare.sync", return_value=None) as sync_mock:
                result = prepare(cfg, log=lambda m: None)
            core.assert_called_once()
            sync_mock.assert_called_once()
            self.assertTrue(result.installed)
            self.assertTrue(result.synced)


if __name__ == "__main__":
    unittest.main()
