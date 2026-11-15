import importlib.util
from importlib.machinery import SourceFileLoader
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load("split_editor", ROOT / "codex-split-editor")
launcher = load("split_launcher", ROOT / "codex-split")


class EditorArgumentTests(unittest.TestCase):
    def test_editor_command_is_split_without_shell_evaluation(self):
        with patch.dict(os.environ, {"PATH": os.environ["PATH"], "CODEX_SPLIT_EDITOR": "python3 -I"}, clear=True):
            self.assertEqual(helper.editor_argv(None, ["a file.txt"]), [shutil.which("python3"), "-I", "a file.txt"])

    def test_rejects_malformed_editor(self):
        with patch.dict(os.environ, {"CODEX_SPLIT_EDITOR": "'unfinished"}, clear=True):
            with self.assertRaises(helper.EditorError):
                helper.editor_argv(None, ["file"])

    def test_layout_and_backend_options(self):
        args = helper.parse_args(["--backend", "zellij", "--layout", "vertical", "file with spaces"])
        self.assertEqual((args.backend, args.layout, args.files), ("zellij", "vertical", ["file with spaces"]))


class BackendTests(unittest.TestCase):
    @patch.object(helper, "check_dependency")
    @patch.object(helper, "tmux_inside", return_value=7)
    def test_tmux_uses_inside_pane_backend(self, inside, dependency):
        with patch.dict(os.environ, {"TMUX": "session", "TMUX_PANE": "%1"}):
            self.assertEqual(helper.open_tmux(["vim", "file"], "vertical"), 7)
        dependency.assert_called_once_with("tmux")
        inside.assert_called_once_with(["vim", "file"], "vertical")

    @patch.object(helper, "check_dependency")
    def test_zellij_uses_blocking_worker_and_layout_direction(self, dependency):
        with tempfile.TemporaryDirectory() as tempdir:
            marker_dir = Path(tempdir) / "markerdir"
            marker_dir.mkdir()
            Path(marker_dir, "status").write_text("0")
            def fake_run(argv, **kwargs):
                output = '[{"id":4,"is_focused":true}]' if argv[2:3] == ["list-panes"] else "terminal_5" if argv[2:3] == ["new-pane"] else ""
                return helper.subprocess.CompletedProcess(argv, 0, output, "")
            with patch.dict(os.environ, {"ZELLIJ": "0"}, clear=True), \
                 patch.object(helper.tempfile, "mkdtemp", return_value=str(marker_dir)), \
                 patch.object(helper.Path, "read_text", return_value="0"), \
                 patch.object(helper, "run", side_effect=fake_run) as run:
                self.assertEqual(helper.open_zellij(["nano", "file"], "vertical"), 0)
            argv = run.call_args_list[1].args[0]
            self.assertIn("--direction", argv)
            self.assertIn("down", argv)
            self.assertIn("--close-on-exit", argv)

    @patch.object(launcher.subprocess, "run")
    def test_launcher_forwards_codex_arguments_and_installs_visual(self, run):
        run.return_value = helper.subprocess.CompletedProcess([], 0)
        with patch.dict(os.environ, {"TMUX": "inside"}, clear=True), \
             patch.object(launcher.sys, "argv", ["codex-split", "--codex-bin", "/bin/echo", "--", "--model", "test model"]):
            self.assertEqual(launcher.main(), 0)
        command = run.call_args.args[0]
        env = run.call_args.kwargs["env"]
        self.assertEqual(command, ["/bin/echo", "--model", "test model"])
        self.assertTrue(env["VISUAL"].endswith("codex-split-editor"))
        self.assertNotEqual(env["VISUAL"], env.get("EDITOR"))

    @patch.object(launcher.subprocess, "run")
    def test_new_zellij_session_uses_private_codex_keybindings(self, run):
        config_contents = []
        def fake_run(command, **kwargs):
            config_contents.append(Path(command[command.index("--config") + 1]).read_text())
            return helper.subprocess.CompletedProcess(command, 0)
        run.side_effect = fake_run
        with patch.dict(os.environ, {"PATH": os.environ["PATH"]}, clear=True), \
             patch.object(launcher.sys, "argv", ["codex-split", "--backend", "zellij", "--editor", "/bin/echo", "--codex-bin", "/bin/echo"]):
            self.assertEqual(launcher.main(), 0)
        command = run.call_args.args[0]
        self.assertIn("--config", command)
        self.assertIn("show_startup_tips false", config_contents[0])
        self.assertIn('unbind "Ctrl g"', config_contents[0])
        self.assertIn('bind "Ctrl Alt g"', config_contents[0])


if __name__ == "__main__":
    unittest.main()
