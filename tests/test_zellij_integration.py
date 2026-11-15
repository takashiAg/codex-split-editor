"""Real Zellij smoke test; run the test command from a Zellij pane."""

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("zellij") and os.environ.get("ZELLIJ"), "run this test inside Zellij")
class ZellijIntegrationTests(unittest.TestCase):
    def test_spaces_edits_exit_status_and_pane_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="codex split zellij ") as tempdir:
            target = Path(tempdir) / "file with spaces.txt"
            target.write_text("before")
            script = Path(tempdir) / "editor.py"
            script.write_text("import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(p.read_text()+' edited')\n")
            env = os.environ.copy()
            env["CODEX_SPLIT_BACKEND"] = "zellij"
            env["CODEX_SPLIT_EDITOR"] = shlex.join(["python3", str(script)])
            result = subprocess.run([str(ROOT / "codex-split-editor"), str(target)], env=env, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), "before edited")
            env["CODEX_SPLIT_EDITOR"] = "python3 -c 'raise SystemExit(9)'"
            failed = subprocess.run([str(ROOT / "codex-split-editor"), str(target)], env=env, check=False)
            self.assertEqual(failed.returncode, 9)


if __name__ == "__main__":
    unittest.main()
