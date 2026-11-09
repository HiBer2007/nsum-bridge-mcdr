import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nsum_bridge.config import Config, DEFAULT_CONFIG
from nsum_bridge.instance import Instance, normalize_loader
from nsum_bridge.sync import build_command, describe_stage
from nsum_bridge.installer import _looks_installed
from nsum_bridge.prepare import prepare


class InstanceTests(unittest.TestCase):
    def test_normalize_loader(self):
        self.assertEqual(normalize_loader("Fabric-Loader"), "fabric")
        self.assertEqual(normalize_loader("neo-forge"), "neoforge")
        self.assertEqual(normalize_loader("vanilla"), "")

    def test_matches(self):
        inst = Instance(game_version="1.21.1", modloader="fabric", modloader_version="0.16.9",
                        installed_game_version="1.21.1", installed_modloader="fabric",
                        installed_loader_version="0.16.9")
        self.assertTrue(inst.matches())
        inst.installed_loader_version = "0.15.11"
        self.assertFalse(inst.matches())
        inst.installed_loader_version = "0.16.9"
        inst.installed_modloader = "neoforge"
        self.assertFalse(inst.matches())

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inst = Instance(repo="r", branch="base", game_version="1.21.1",
                            modloader="fabric", modloader_version="0.16.9",
                            installed_game_version="1.21.1",
                            installed_modloader="fabric",
                            installed_loader_version="0.16.9")
            inst.write(root)
            back = Instance.read(root)
            self.assertEqual(back.repo, "r")
            self.assertEqual(back.installed_loader_version, "0.16.9")


class ConfigTests(unittest.TestCase):
    def test_defaults_and_paths(self):
        base = Path(tempfile.mkdtemp())
        cfg = Config(base_dir=base, raw=dict(DEFAULT_CONFIG))
        self.assertEqual(cfg.branch, "base")
        self.assertEqual(cfg.server_dir, (base / "server").resolve())
        self.assertTrue(cfg.auto_install_core)
        self.assertFalse(cfg.launch_on_sync_failure)

    def test_absolute_server_dir(self):
        absolute = Path(tempfile.mkdtemp()) / "mc"
        raw = dict(DEFAULT_CONFIG)
        raw["server_dir"] = str(absolute)
        cfg = Config(base_dir=Path(tempfile.mkdtemp()), raw=raw)
        self.assertEqual(cfg.server_dir, absolute)


class SyncTests(unittest.TestCase):
    def test_build_command(self):
        runtime = Path(tempfile.mkdtemp()) / "NeoServerUpdateModpack"
        server = Path(tempfile.mkdtemp()) / "mc"
        cmd = build_command(runtime, "git@x/y.git", "base", "main", server)
        self.assertEqual(cmd[:4], [str(runtime), "exec", "build", "--repo"])
        self.assertIn("--git-branch", cmd)
        self.assertEqual(cmd[-4:], ["--format", "hmcl", "--export", str(server)])

    def test_describe_stage(self):
        self.assertEqual(describe_stage("process_files"), "处理文件")
        self.assertEqual(describe_stage("unknown"), "unknown")


class InstallerTests(unittest.TestCase):
    def test_looks_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(_looks_installed(root, "fabric"))
            (root / "fabric-server-launch.jar").write_bytes(b"x")
            self.assertTrue(_looks_installed(root, "fabric"))
            self.assertFalse(_looks_installed(root, ""))


class PrepareTests(unittest.TestCase):
    def _config(self, tmp, repo="git@x/y.git"):
        raw = dict(DEFAULT_CONFIG)
        raw.update({"repo": repo, "server_dir": "server"})
        return Config(base_dir=Path(tmp), raw=raw)

    def test_prepare_missing_marker_without_repo_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(tmp, repo="")
            with self.assertRaises(RuntimeError):
                prepare(cfg, log=lambda m: None)

    def test_prepare_syncs_and_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._config(tmp)
            inst = Instance(repo=cfg.repo, branch="base", game_version="1.21.1",
                            modloader="fabric", modloader_version="0.16.9")
            inst.write(cfg.server_dir)
            with mock.patch("nsum_bridge.prepare.ensure_core", return_value=True) as core, \
                 mock.patch("nsum_bridge.prepare.sync", return_value=None) as sync_mock:
                result = prepare(cfg, log=lambda m: None)
            core.assert_called_once()
            sync_mock.assert_called_once()
            self.assertTrue(result.installed)
            self.assertTrue(result.synced)


if __name__ == "__main__":
    unittest.main()
