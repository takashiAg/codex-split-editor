"""Real tmux split smoke test, isolated with a private tmux socket."""

import os
import json
import shlex
import shutil
import subprocess
import tempfile
import shutil as file_shutil
import time
import pty
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
            env = os.environ.copy() | {"CODEX_HOME": str(temp / "server-stale")}
            env.pop("TMUX", None)
            env.pop("TMUX_PANE", None)
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
                    self.assertEqual(process.wait(timeout=5), 2)
                    helper_env.pop("CODEX_SPLIT_LAYOUT", None)

                # Exercise ordinary Codex entry through the installed runtime
                # in a real PTY. This proves VISUAL stays per-process and the
                # editor gets a filename containing spaces.
                edited = temp / "through launcher.txt"
                edited.write_text("start")
                editor_stub = temp / "fake editor.py"
                editor_stub.write_text("import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+' called')\n")
                codex_stub = temp / "fake codex.py"
                codex_stub.write_text(
                    "import os,shlex,subprocess,sys; assert sys.argv[1:]==['--flag','value with spaces']; "
                    "assert os.environ['EDITOR']=='untouched-editor'; "
                    "subprocess.run(shlex.split(os.environ['VISUAL'])+[os.environ['EDIT_TARGET']],check=True)\n"
                )
                codex_stub.chmod(0o755)
                codex_stub.write_text("#!/usr/bin/env python3\n" + codex_stub.read_text())
                xdg_config = temp / "config with spaces"
                xdg_data = temp / "data with spaces"
                runtime = xdg_data / "codex-split-editor"
                runtime.mkdir(parents=True)
                import json
                (xdg_config / "codex-split-editor").mkdir(parents=True)
                (xdg_config / "codex-split-editor/config.json").write_text(json.dumps({
                    "codex_bin": str(codex_stub), "backend": "tmux", "layout": "horizontal",
                    "editor": shlex.join(["python3", str(editor_stub)]),
                }))
                shutil.copy2(ROOT / "codex-split-editor", runtime / "codex-split-editor")
                launch_env = env | {
                    "HOME": str(temp), "XDG_CONFIG_HOME": str(xdg_config), "XDG_DATA_HOME": str(xdg_data),
                    "EDIT_TARGET": str(edited), "EDITOR": "untouched-editor", "PATH": str(temp) + os.pathsep + env["PATH"],
                }
                test_vars = {key: launch_env[key] for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "EDIT_TARGET", "EDITOR", "PATH")}
                launch_command = shlex.join(["env", *[f"{key}={value}" for key, value in test_vars.items()],
                                             str(ROOT / "codex-split"), "--flag", "value with spaces"])
                window = subprocess.run([str(wrapper), "new-window", "-d", "-t", "smoke", "-n", "launch",
                                         "--", "sh", "-c", launch_command], env=env, check=False,
                                        capture_output=True, text=True)
                self.assertEqual(window.returncode, 0, window.stderr)
                for _ in range(100):
                    if edited.read_text() != "start":
                        break
                    time.sleep(0.05)
                self.assertEqual(edited.read_text(), "start called")

                # Outside tmux, the launcher creates/attaches its own session.
                # A pre-existing server may have stale environment values; the
                # private bootstrap must give Codex the current caller values.
                report = temp / "launcher env.json"
                stop = temp / "stop launcher"
                external_codex = temp / "external codex.py"
                external_codex.write_text(
                    "import json,os,sys,time; "
                    "json.dump({'env':{k:os.environ.get(k) for k in ('HOME','PATH','CODEX_HOME','OPENAI_API_KEY','VISUAL')},'argv':sys.argv[1:]},open(os.environ['ENV_REPORT'],'w')); "
                    "open(os.environ['ENV_READY'],'w').close(); "
                    "exec('while not os.path.exists(os.environ[\"ENV_STOP\"]): time.sleep(.03)')\n"
                )
                external_codex.chmod(0o755)
                external_codex.write_text("#!/usr/bin/env python3\n" + external_codex.read_text())
                (xdg_config / "codex-split-editor/config.json").write_text(json.dumps({
                    "codex_bin": str(external_codex), "backend": "tmux", "layout": "horizontal", "editor": "nano",
                }))
                (temp / "launcher ready").unlink(missing_ok=True)
                external_env = os.environ.copy() | {
                    "HOME": str(temp), "PATH": str(temp) + os.pathsep + os.environ.get("PATH", ""),
                    "XDG_CONFIG_HOME": str(xdg_config), "XDG_DATA_HOME": str(xdg_data),
                    "CODEX_HOME": str(temp / "caller-codex-home"), "OPENAI_API_KEY": "test-key-only",
                    "ENV_REPORT": str(report), "ENV_READY": str(temp / "launcher ready"), "ENV_STOP": str(stop),
                }
                external_env.pop("TMUX", None)
                external_env.pop("TMUX_PANE", None)
                master, slave = pty.openpty()
                attached = subprocess.Popen([str(ROOT / "codex-split")], env=external_env,
                                            stdin=slave, stdout=slave, stderr=slave, close_fds=True)
                os.close(slave)
                try:
                    for _ in range(150):
                        if (temp / "launcher ready").exists():
                            break
                        if attached.poll() is not None:
                            break
                        time.sleep(0.05)
                    self.assertTrue((temp / "launcher ready").exists(), "Codex did not start in the new tmux session")
                    result = json.loads(report.read_text())
                    values = result["env"]
                    self.assertEqual(values["CODEX_HOME"], str(temp / "caller-codex-home"))
                    self.assertEqual(values["OPENAI_API_KEY"], "test-key-only")
                    self.assertEqual(values["HOME"], str(temp))
                    self.assertEqual(values["VISUAL"], str(runtime / "codex-split-editor"))
                    self.assertIn("--no-alt-screen", result["argv"])
                finally:
                    stop.touch()
                    try:
                        attached.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        attached.kill()
                        attached.wait()
                    os.close(master)
            finally:
                subprocess.run([str(wrapper), "kill-server"], env=env, check=False)
                file_shutil.rmtree(socket_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
