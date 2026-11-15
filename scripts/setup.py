#!/usr/bin/env python3
"""Install or remove the Codex split-editor shell integration (macOS)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).absolute()
ROOT = SCRIPT.parents[1] if SCRIPT.parent.name == "scripts" else SCRIPT.parent
START = "# >>> codex-split-editor managed block >>>"
END = "# <<< codex-split-editor managed block <<<"
FILES = ("codex-split", "codex-split-editor", "setup.py")


class SetupError(RuntimeError):
    pass


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))


def config_path() -> Path:
    return config_home() / "codex-split-editor/config.json"


def detect_shell(explicit: str | None) -> tuple[str, str | None]:
    detected = Path(os.environ.get("SHELL", "")).name
    selected = explicit or (detected if detected in {"fish", "zsh", "bash"} else "")
    if selected not in {"fish", "zsh", "bash"}:
        raise SetupError("Could not detect a supported shell; use --shell fish, zsh, or bash.")
    return selected, detected if detected and detected != selected else None


def plugin_root(source: str | None) -> Path:
    path = Path(source or os.environ.get("PLUGIN_ROOT") or ROOT).expanduser().absolute()
    if not path.is_dir():
        raise SetupError(f"Plugin source directory does not exist: {path}")
    for name in ("codex-split", "codex-split-editor", "scripts/setup.py"):
        if not (path / name).is_file():
            raise SetupError(f"Plugin source is missing {name}: {path}")
    return path


def codex_binary(previous: dict | None) -> str:
    if previous and previous.get("codex_bin") and Path(previous["codex_bin"]).is_file():
        return previous["codex_bin"]
    found = shutil.which("codex")
    if not found:
        raise SetupError("Codex CLI was not found on PATH. Install Codex, then rerun setup.")
    # Preserve a Homebrew symlink so normal upgrades do not stale the path.
    return os.path.abspath(found)


def check_macos() -> None:
    if sys.platform != "darwin":
        raise SetupError("This setup currently supports macOS only.")


def check_tools(backend: str, editor: str, install_deps: bool) -> None:
    try:
        editor_argv = shlex.split(editor)
    except ValueError as exc:
        raise SetupError(f"Invalid editor command: {exc}") from exc
    if not editor_argv:
        raise SetupError("Editor command is empty.")
    missing = [tool for tool in (backend, editor_argv[0], "less") if not shutil.which(tool)]
    if missing and install_deps:
        brew = shutil.which("brew")
        formulae = {"tmux": "tmux", "zellij": "zellij", "nano": "nano", "vim": "vim", "nvim": "neovim", "less": "less"}
        if not brew or any(tool not in formulae for tool in missing):
            raise SetupError("Homebrew cannot install the missing selected tool(s): " + ", ".join(missing))
        subprocess.run([brew, "install", *dict.fromkeys(formulae[tool] for tool in missing)], check=True)
        missing = [tool for tool in missing if not shutil.which(tool)]
    if missing:
        raise SetupError(f"Missing required tool(s): {', '.join(missing)}. Install them, or pass --install-deps for Homebrew.")


def read_state() -> dict | None:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"Cannot read setup state at {config_path()}: {exc}") from exc


def shell_path(shell: str) -> Path:
    if shell == "fish":
        return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fish/functions/codex.fish"
    return Path.home() / (".zshrc" if shell == "zsh" else ".bashrc")


def fish_function(runtime: Path) -> str:
    return f'''# Managed by Codex Split Editor. Uninstall with: python3 {shlex.quote(str(runtime / "setup.py"))} uninstall
function codex
    command python3 {shlex.quote(str(runtime / "codex-split"))} $argv
end
'''


def rc_block(runtime: Path) -> str:
    runtime_var = shlex.quote(str(runtime))
    return f'''{START}
codex() {{
    command python3 {runtime_var}/codex-split "$@"
}}
{END}'''


def shell_content(shell: str, path: Path, runtime: Path, old: dict | None) -> tuple[bytes, dict]:
    desired = fish_function(runtime) if shell == "fish" else rc_block(runtime)
    if old:
        if old.get("shell") != shell or old.get("integration_path") != str(path):
            raise SetupError("An installation for another shell/path exists. Uninstall it before changing shells.")
        if not path.is_file():
            raise SetupError(f"Installed shell integration is missing: {path}")
        current = path.read_text(encoding="utf-8")
        if old["integration_kind"] == "fish":
            if current != old["integration_text"]:
                raise SetupError(f"Managed fish function changed since setup: {path}; restore it before updating.")
            result = desired
        else:
            before, sep, tail = current.partition(START)
            body, end_sep, after = tail.partition(END) if sep else ("", "", "")
            if not end_sep or START + body + END != old["integration_text"] or START in after or END in after:
                raise SetupError(f"Managed shell block changed since setup: {path}; restore it before updating.")
            result = before + desired + after
        meta = {"integration_original": old.get("integration_original", ""),
                "integration_existed": old.get("integration_existed", True)}
        return result.encode(), {"integration_kind": old["integration_kind"], "integration_text": desired, **meta}

    if shell == "fish":
        if path.exists():
            raise SetupError(f"A fish function already exists: {path}. Preserve or rename it before setup.")
        return desired.encode(), {"integration_kind": "fish", "integration_text": desired,
                                  "integration_original": "", "integration_existed": False}
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if re.search(r"(?m)^\s*(?:codex\s*\(\)|function\s+codex(?:\s|\()|alias\s+codex=)", original):
        raise SetupError(f"A custom codex function or alias exists in {path}. Merge it manually before setup.")
    if START in original or END in original:
        raise SetupError(f"Managed block markers already exist in {path}; refusing to overwrite them.")
    separator = "" if not original or original.endswith("\n") else "\n"
    result = original + separator + desired + "\n"
    return result.encode(), {"integration_kind": "rc", "integration_text": desired,
                             "integration_original": original, "integration_existed": path.exists()}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare_runtime(source: Path, runtime: Path, old: dict | None) -> tuple[dict[str, bytes], dict[str, bytes | None]]:
    if runtime.exists() and not runtime.is_dir():
        raise SetupError(f"Runtime path is not a directory: {runtime}")
    old_hashes = (old or {}).get("runtime_files", {})
    if old is None and runtime.exists():
        raise SetupError(f"Runtime directory already exists without setup ownership: {runtime}")
    new_files: dict[str, bytes] = {}
    backup: dict[str, bytes | None] = {}
    for name in FILES:
        source_path = source / ("scripts/setup.py" if name == "setup.py" else name)
        target = runtime / name
        data = source_path.read_bytes()
        if target.is_symlink():
            raise SetupError(f"Refusing to replace runtime symlink: {target}")
        if target.exists():
            if name not in old_hashes or not target.is_file() or digest(target.read_bytes()) != old_hashes[name]:
                raise SetupError(f"Refusing to overwrite an unowned or edited runtime file: {target}")
            backup[name] = target.read_bytes()
        else:
            if name in old_hashes:
                raise SetupError(f"Previously installed runtime file is missing: {target}")
            backup[name] = None
        new_files[name] = data
    return new_files, backup


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def rollback_runtime(runtime: Path, backup: dict[str, bytes | None]) -> None:
    for name, data in backup.items():
        target = runtime / name
        if data is None:
            target.unlink(missing_ok=True)
        else:
            atomic_write(target, data, 0o755)
    try:
        runtime.rmdir()
    except OSError:
        pass


def setup(args: argparse.Namespace) -> int:
    check_macos()
    shell, mismatch = detect_shell(args.shell)
    old = read_state()
    backend = args.backend or (old or {}).get("backend", "tmux")
    layout = args.layout or (old or {}).get("layout", "horizontal")
    editor = args.editor or (old or {}).get("editor", "nano")
    if backend not in {"tmux", "zellij"} or layout not in {"horizontal", "vertical"}:
        raise SetupError("Invalid backend or layout selection.")
    check_tools(backend, editor, args.install_deps)
    source = plugin_root(args.source)
    codex = codex_binary(old)
    runtime = data_home() / "codex-split-editor"
    integration = shell_path(shell)
    shell_bytes, shell_meta = shell_content(shell, integration, runtime, old)
    new_files, backup = prepare_runtime(source, runtime, old)
    old_shell = integration.read_bytes() if integration.exists() else None
    state_path = config_path()
    old_state = state_path.read_bytes() if state_path.exists() else None
    state = {
        "version": 1, "shell": shell, "backend": backend, "layout": layout, "editor": editor,
        "codex_bin": codex, "runtime_path": str(runtime), "integration_path": str(integration),
        **shell_meta, "runtime_files": {name: digest(data) for name, data in new_files.items()},
    }
    try:
        runtime.mkdir(parents=True, exist_ok=True)
        for name, data in new_files.items():
            atomic_write(runtime / name, data, 0o755)
        atomic_write(integration, shell_bytes)
        atomic_write(state_path, (json.dumps(state, indent=2) + "\n").encode(), 0o600)
    except Exception:
        if old_shell is None:
            integration.unlink(missing_ok=True)
        else:
            atomic_write(integration, old_shell)
        if old_state is None:
            state_path.unlink(missing_ok=True)
        else:
            atomic_write(state_path, old_state, 0o600)
        rollback_runtime(runtime, backup)
        raise
    if mismatch:
        print(f"Detected SHELL={mismatch}; installed {shell} as explicitly requested.", file=sys.stderr)
    print(f"Installed {shell} integration at {integration}")
    print("Open one fresh terminal so the new shell function is loaded.")
    print(f"Backend: {backend}; layout: {layout}; editor: {editor}")
    print("Use codex or codex resume as usual, then press Ctrl+G to edit the draft.")
    return 0


def uninstall() -> int:
    state = read_state()
    if not state:
        print("Codex split-editor setup is not installed.")
        return 0
    path = Path(state["integration_path"])
    runtime = Path(state.get("runtime_path", data_home() / "codex-split-editor"))
    hashes = state.get("runtime_files", {})
    # Validate every owned target before changing either the shell or runtime.
    for name, expected in hashes.items():
        target = runtime / name
        if target.is_symlink() or not target.is_file() or digest(target.read_bytes()) != expected:
            raise SetupError(f"Preserving edited/missing runtime file: {target}. Restore it before uninstall.")
    if not path.is_file():
        raise SetupError(f"Cannot safely uninstall: managed integration is missing from {path}.")
    text = path.read_text(encoding="utf-8")
    if state["integration_kind"] == "fish":
        if text != state["integration_text"]:
            raise SetupError(f"The fish function changed; preserving your edits in {path}.")
        path.unlink()
    else:
        before, sep, tail = text.partition(START)
        body, end_sep, after = tail.partition(END) if sep else ("", "", "")
        if not end_sep or START + body + END != state["integration_text"]:
            raise SetupError(f"The managed shell block changed; preserving {path}.")
        remaining = before + after
        original = state.get("integration_original", "")
        separator = "" if not original or original.endswith("\n") else "\n"
        installed_baseline = original + separator + state["integration_text"] + "\n"
        if text == installed_baseline and not state.get("integration_existed", True):
            path.unlink()
        elif text == installed_baseline:
            atomic_write(path, original.encode())
        else:
            atomic_write(path, remaining.encode())

    for name in hashes:
        (runtime / name).unlink(missing_ok=True)
    try:
        runtime.rmdir()
    except OSError:
        pass  # Preserve user-added files in the runtime directory.
    config_path().unlink(missing_ok=True)
    print("Removed the Codex shell integration and owned files. Plugin removal is separate: codex plugin remove codex-split-editor@codex-split-editor")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install or uninstall the Codex split-editor shell integration.")
    sub = parser.add_subparsers(dest="action", required=True)
    install = sub.add_parser("setup", help="install/update the shell integration")
    install.add_argument("--source", help="plugin package directory")
    install.add_argument("--shell", choices=("fish", "zsh", "bash"))
    install.add_argument("--backend", choices=("tmux", "zellij"))
    install.add_argument("--layout", choices=("horizontal", "vertical"))
    install.add_argument("--editor")
    install.add_argument("--install-deps", action="store_true")
    sub.add_parser("uninstall", help="remove only this setup's function and files")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return setup(args) if args.action == "setup" else uninstall()
    except (SetupError, OSError, subprocess.CalledProcessError) as exc:
        print(f"codex-split-editor setup: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
