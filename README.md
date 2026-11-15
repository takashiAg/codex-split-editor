# codex-split-editor

[日本語](README.ja.md)

Run Codex CLI in tmux or Zellij and open its external-editor request in a normal terminal editor in a neighboring pane. tmux is the default. Codex waits while the editor is open; when you save and quit, focus returns to Codex. The editor's exit code is returned to Codex.

Supported on macOS and Linux. WSL has not been tested.

## Requirements

- Python 3.10 or newer
- Codex CLI
- tmux (default backend) or Zellij (optional backend)
- An editor such as `nano`, `vim`, or `nvim`

Zellij users need version 0.46 or newer for the pane lifecycle commands used here. On macOS, install the backend you want with `brew install tmux` or `brew install zellij`.

Install the multiplexer yourself. This tool does not install software or change shell startup files.

## Install

```sh
git clone https://github.com/takashiAg/codex-split-editor.git
cd codex-split-editor
mkdir -p ~/.local/bin
ln -s "$PWD/codex-split" "$HOME/.local/bin/codex-split"
ln -s "$PWD/codex-split-editor" "$HOME/.local/bin/codex-split-editor"
```

Ensure `~/.local/bin` is on `PATH`, then start Codex through the launcher:

For fish, add the directory to the current shell with `fish_add_path ~/.local/bin`.

```sh
codex-split
codex-split --editor vim -- --model your-model
codex-split --backend zellij --editor 'nvim -u NONE'
codex-split --layout vertical -- resume
```

`--layout horizontal` places the editor left/right; `--layout vertical` places it top/bottom. `--editor` accepts a command with arguments. The default editor is `nano`; `CODEX_SPLIT_EDITOR`, `CODEX_SPLIT_BACKEND`, and `CODEX_SPLIT_LAYOUT` can set defaults.

The launcher reuses an existing session when already inside the selected multiplexer. Outside one, it creates a session and starts Codex there. New Zellij sessions use a temporary, session-only config that hides first-run tips and frees Ctrl+G for Codex; Ctrl+Alt+G locks or unlocks the Zellij UI. Existing Zellij sessions keep their current keybindings, so rebind Ctrl+G there if it currently toggles the locked mode. If Codex is already running outside tmux/Zellij, invoke the launcher in a new terminal session to use split editing.

In Codex, press **Ctrl+G** to open the editor. In nano, save with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**. In Vim, save and exit with `:wq`.

## Uninstall

Remove the two symlinks and, if desired, the cloned directory:

```sh
rm "$HOME/.local/bin/codex-split" "$HOME/.local/bin/codex-split-editor"
rm -rf /path/to/codex-split-editor
```

## Development

Run tests with `python3 -m unittest discover -s tests`. The tmux integration test uses a private temporary server. Run `tests/run_zellij_integration.sh` to exercise Zellij 0.46.0 in a bounded background session; it verifies the editor behavior and fails if the test is skipped.

## CI and releases

Pull requests and pushes to `main` run the required `CI` check. It covers Python 3.10 and 3.13 on Ubuntu, Python 3.13 on macOS, and a pinned Zellij 0.46.0 integration run. Main is protected: changes merge through pull requests after CI passes. Reviews are optional; the repository does not require an approval count.

To prepare a release, run the **Release** workflow from `main` with a `vMAJOR.MINOR.PATCH` version. The default dry run validates the request, reruns CI, builds a distributable archive and SHA-256 file, and uploads them as a workflow artifact. Turn off dry run only when ready to create the version tag and GitHub release. Existing tags and releases are never overwritten.

## License

MIT. See [LICENSE](LICENSE).

