"""Real tmux split smoke test, isolated with a private tmux socket."""

import os
import shlex
import shutil
import subprocess
import tempfile
import shutil as file_shutil
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TmuxIntegrationTests(unittest.TestCase):
    def test_spaces_edits_exit_status_and_pane_cleanup(self):
        if not shutil.which("tmux"):
            if os.environ.get("CI"):
                self.fail("tmux is required in CI")
            self.skipTest("tmux is not installed")
        with tempfile.TemporaryDirectory(prefix="codex split test ") as tempdir:
            temp = Path(tempdir)
            socket = "codex-split-test-" + str(os.getpid())
            wrapper = temp / "tmux"
            actual_tmux = shutil.which("tmux")
            wrapper.write_text(f"#!/bin/sh\nexec {actual_tmux} -L {socket} \"$@\"\n")
            wrapper.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(temp) + os.pathsep + env["PATH"]
            socket_dir = tempfile.mkdtemp(prefix="ts-", dir=str(Path.home()))
            env["TMUX_TMPDIR"] = socket_dir
            start = subprocess.run([str(wrapper), "new-session", "-d", "-s", "smoke", "-x", "100", "-y", "30"], env=env, capture_output=True, text=True)
            if start.returncode:
                file_shutil.rmtree(socket_dir, ignore_errors=True)
                if os.environ.get("CI"):
                    self.fail(f"tmux server sockets unavailable: {start.stderr.strip()}")
                self.skipTest(f"tmux server sockets unavailable: {start.stderr.strip()}")
            try:
                pane = subprocess.check_output([str(wrapper), "display-message", "-p", "-t", "smoke:0", "#{pane_id}"], env=env, text=True).strip()
                target = temp / "file with spaces.txt"
                target.write_text("before")
                helper_env = env | {"TMUX": "private", "TMUX_PANE": pane}
                script = temp / "editor.py"
                script.write_text("import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(pathlib.Path(sys.argv[1]).read_text()+' edited')\n")
                helper_env["CODEX_SPLIT_EDITOR"] = shlex.join(["python3", str(script)])
                helper = subprocess.run([str(ROOT / "codex-split-editor"), str(target)], env=helper_env, check=False)
                self.assertEqual(helper.returncode, 0)
                self.assertEqual(target.read_text(), "before edited")
                helper_env["CODEX_SPLIT_EDITOR"] = "python3 -c 'raise SystemExit(9)'"
                failed = subprocess.run([str(ROOT / "codex-split-editor"), str(target)], env=helper_env, check=False)
                self.assertEqual(failed.returncode, 9)
                panes = subprocess.check_output([str(wrapper), "list-panes", "-t", "smoke:0", "-F", "#{pane_id}"], env=env, text=True).splitlines()
                self.assertEqual(panes, [pane])

                # Check left/right and top/bottom geometry while the editor is live.
                for layout, dimension in (("horizontal", "#{pane_width}"), ("vertical", "#{pane_height}")):
                    blocker = temp / f"block-{layout}.py"
                    blocker.write_text("import time; time.sleep(30)\n")
                    helper_env["CODEX_SPLIT_EDITOR"] = shlex.join(["python3", str(blocker)])
                    helper_env["CODEX_SPLIT_LAYOUT"] = layout
                    process = subprocess.Popen([str(ROOT / "codex-split-editor"), str(target)], env=helper_env)
                    split = None
                    for _ in range(100):
                        active = subprocess.check_output([str(wrapper), "list-panes", "-t", "smoke:0", "-F", "#{pane_id}"], env=env, text=True).splitlines()
                        if len(active) > 1:
                            split = next(item for item in active if item != pane)
                            break
                        time.sleep(0.05)
                    self.assertIsNotNone(split, "editor pane was not created")
                    parent_size = int(subprocess.check_output([str(wrapper), "display-message", "-p", "-t", pane, dimension], env=env, text=True))
                    child_size = int(subprocess.check_output([str(wrapper), "display-message", "-p", "-t", split, dimension], env=env, text=True))
                    self.assertLess(child_size, parent_size)
                    subprocess.run([str(wrapper), "kill-pane", "-t", split], env=env, check=True)
                    self.assertEqual(process.wait(timeout=5), 1)
                    helper_env.pop("CODEX_SPLIT_LAYOUT", None)

                # The launcher exports VISUAL and forwards Codex arguments.
                edited = temp / "through launcher.txt"
                edited.write_text("start")
                editor_stub = temp / "fake editor.py"
                editor_stub.write_text("import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+' called')\n")
                codex_stub = temp / "fake codex.py"
                codex_stub.write_text(
                    "import os,shlex,subprocess,sys; assert sys.argv[1:3]==['--flag','value with spaces']; "
                    "subprocess.run(shlex.split(os.environ['VISUAL'])+[sys.argv[3]],check=True)\n"
                )
                codex_stub.chmod(0o755)
                codex_stub.write_text("#!/usr/bin/env python3\n" + codex_stub.read_text())
                launcher_env = helper_env | {"TMUX": "private", "TMUX_PANE": pane}
                launched = subprocess.run([str(ROOT / "codex-split"), "--codex-bin", str(codex_stub),
                                           "--editor", shlex.join(["python3", str(editor_stub)]), "--",
                                           "--flag", "value with spaces", str(edited)], env=launcher_env, check=False)
                self.assertEqual(launched.returncode, 0)
                self.assertEqual(edited.read_text(), "start called")
            finally:
                subprocess.run([str(wrapper), "kill-server"], env=env, check=False)
                file_shutil.rmtree(socket_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
