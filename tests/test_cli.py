"""Focused unit coverage for the internal launcher, editor helper, and setup."""

import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load("split_editor", ROOT / "codex-split-editor")
launcher = load("split_launcher", ROOT / "codex-split")
setup_tool = load("split_setup", ROOT / "scripts/setup.py")


class EditorHelperTests(unittest.TestCase):
    def test_snapshot_removes_terminal_controls_and_keeps_unicode(self):
        self.assertEqual(helper.safe_text("a\x1b[31m日本\x9bZ\x07\nb"), "a[31m日本Z\nb")

    def test_editor_command_preserves_spaces_as_one_filename(self):
        argv = helper.editor_command("python3 -I", "/tmp/a file.md")
        self.assertTrue(Path(argv[0]).is_absolute())
        self.assertEqual(argv[1:], ["-I", "/tmp/a file.md"])

    def test_wait_rechecks_status_after_pane_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "status"
            class Pager:
                def poll(self): return None
                def terminate(self): pass
            def dead(_pane):
                marker.write_text("9")
                return False
            code, completed = helper.wait_for_editor(marker, "%2", dead, Pager())
            self.assertEqual((code, completed), (9, True))


class LauncherTests(unittest.TestCase):
    def test_command_classification_does_not_misread_option_values(self):
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), \
             patch.object(launcher.sys.stdout, "isatty", return_value=True), \
             patch.object(launcher.sys.stderr, "isatty", return_value=True):
            self.assertFalse(launcher.is_interactive_codex(["-m", "exec", "--help"]))
            self.assertFalse(launcher.is_interactive_codex(["-c", "profile=plugin", "plugin", "list"]))
            self.assertTrue(launcher.is_interactive_codex(["please explain exec syntax"]))

    def test_noninteractive_commands_are_not_wrapped(self):
        with patch.object(launcher, "load_config", return_value={
            "codex_bin": "/bin/echo", "backend": "tmux", "layout": "horizontal", "editor": "nano",
        }), patch.object(launcher.sys.stdin, "isatty", return_value=False), patch.object(launcher.sys.stdout, "isatty", return_value=False), \
             patch.object(launcher.sys.stderr, "isatty", return_value=False), patch.object(launcher.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(launcher.main(["resume"]), 0)
            self.assertEqual(run.call_args.args[0], ["/bin/echo", "resume"])
            self.assertNotIn("env", run.call_args.kwargs)


class SetupOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="split setup ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.config = self.home / "cfg space"
        self.data = self.home / "data space"
        self.bin = self.home / "bin"
        self.bin.mkdir()
        fake_codex = self.bin / "codex"
        fake_codex.write_text("#!/bin/sh\nexit 0\n")
        fake_codex.chmod(0o755)
        self.environment = {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.config), "XDG_DATA_HOME": str(self.data),
            "SHELL": "/bin/zsh", "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
        }
        self.macos = patch.object(setup_tool.sys, "platform", "darwin")
        self.macos.start()
        self.addCleanup(self.macos.stop)
        self.check_tools = patch.object(setup_tool, "check_tools")
        self.check_tools.start()
        self.addCleanup(self.check_tools.stop)

    def install(self, *args):
        with patch.dict(os.environ, self.environment, clear=True):
            return setup_tool.main(["setup", "--source", str(ROOT), *args])

    def uninstall(self):
        with patch.dict(os.environ, self.environment, clear=True):
            return setup_tool.main(["uninstall"])

    def test_install_update_and_uninstall_preserve_other_runtime_data(self):
        self.assertEqual(self.install(), 0)
        state_path = self.config / "codex-split-editor/config.json"
        runtime = self.data / "codex-split-editor"
        notes = runtime / "user-notes"
        notes.write_text("keep")
        self.assertEqual(self.install("--backend", "zellij", "--editor", "vim"), 0)
        state = json.loads(state_path.read_text())
        self.assertEqual((state["backend"], state["editor"]), ("zellij", "vim"))
        self.assertEqual(self.uninstall(), 0)
        self.assertEqual(notes.read_text(), "keep")
        self.assertFalse(state_path.exists())
        self.assertFalse((self.home / ".zshrc").exists())

    def test_fish_update_writes_new_function_and_uninstalls(self):
        with patch.dict(os.environ, self.environment | {"SHELL": "/opt/homebrew/bin/fish"}, clear=True):
            self.assertEqual(setup_tool.main(["setup", "--source", str(ROOT)]), 0)
            path = self.config / "fish/functions/codex.fish"
            self.assertIn("setup.py", path.read_text())
            self.assertEqual(setup_tool.main(["setup", "--source", str(ROOT), "--editor", "vim"]), 0)
            state = json.loads((self.config / "codex-split-editor/config.json").read_text())
            self.assertEqual(state["editor"], "vim")
            self.assertEqual(setup_tool.main(["uninstall"]), 0)
            self.assertFalse(path.exists())

    def test_unowned_runtime_collision_does_not_modify_shell(self):
        runtime = self.data / "codex-split-editor"
        runtime.mkdir(parents=True)
        (runtime / "codex-split").write_text("user file")
        self.assertEqual(self.install(), 2)
        self.assertFalse((self.home / ".zshrc").exists())

    def test_runtime_staging_failure_does_not_modify_shell(self):
        with patch.object(setup_tool, "prepare_runtime", side_effect=setup_tool.SetupError("copy failed")):
            self.assertEqual(self.install(), 2)
        self.assertFalse((self.home / ".zshrc").exists())
        self.assertFalse((self.config / "codex-split-editor/config.json").exists())

    def test_zsh_uninstall_restores_existing_rc_exactly(self):
        rc = self.home / ".zshrc"
        original = "export KEEP=1\n"
        rc.write_text(original)
        self.assertEqual(self.install(), 0)
        self.assertEqual(self.uninstall(), 0)
        self.assertEqual(rc.read_text(), original)

    def test_uninstall_preserves_user_edit_outside_managed_block(self):
        self.assertEqual(self.install(), 0)
        rc = self.home / ".zshrc"
        rc.write_text(rc.read_text() + "\nexport AFTER_SETUP=1\n")
        self.assertEqual(self.uninstall(), 0)
        self.assertIn("export AFTER_SETUP=1", rc.read_text())

    def test_runtime_edit_refuses_uninstall_without_removing_shell(self):
        self.assertEqual(self.install(), 0)
        shell = self.home / ".zshrc"
        runtime_script = self.data / "codex-split-editor/codex-split"
        runtime_script.write_text("user edit")
        self.assertEqual(self.uninstall(), 2)
        self.assertIn("managed block", shell.read_text())


if __name__ == "__main__":
    unittest.main()
