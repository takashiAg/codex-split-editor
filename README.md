# Codex Split Editor

[日本語](README.ja.md)

Codex plugin for editing a prompt in a neighboring terminal pane. Install the plugin, run setup once, then use ordinary `codex` and `codex resume` commands. Press **Ctrl+G** in the composer to open the configured editor; save and close to return the draft to Codex, then review and send it yourself.

Supported on macOS. Codex's external-editor flow suspends its current interaction while the editor is open. This plugin shows a frozen, read-only copy of the caller pane's available terminal scrollback in a pager beside the editor; it is not the full saved conversation. It does not send prompts.

## Install

In Codex, add this repository as a local marketplace and install the plugin:

```text
codex plugin marketplace add takashiAg/codex-split-editor
codex plugin add codex-split-editor@codex-split-editor
```

Use the plugin's setup skill when Codex offers onboarding, or ask Codex to set up Codex Split Editor. Setup installs a small shell integration so interactive `codex` and `codex resume` launch in the selected multiplexer. Open one fresh terminal after setup so the new shell function is loaded.

Setup defaults to tmux, a left/right split, and `nano`. Choose Zellij, a top/bottom split, or another editor during setup. It leaves `EDITOR`, global `VISUAL`, unrelated shell files, and existing multiplexer sessions unchanged. It does not install packages unless you request Homebrew dependency installation.

To run setup directly from a checkout, Python 3.10+ is sufficient; pnpm is optional:

```sh
python3 scripts/setup.py setup --shell fish --backend tmux --layout horizontal --editor nano
# or
pnpm run setup -- --shell fish --backend zellij --editor vim
```

Supported shells are fish, zsh, and bash. Select the shell that launches Codex. If a required tool is missing, install it yourself or explicitly request `--install-deps` to install only the selected missing tools with Homebrew.

## Use

In Codex, press **Ctrl+G**. The snapshot pager supports PgUp/PgDn and arrow keys; press `q` to close it. The editor is in the neighboring pane. In nano, save with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**. In Vim, save and exit with `:wq`. Codex returns the edited text to the composer for you to review and send.

tmux is the default backend. Zellij 0.46.0 or newer is required. The setup skill accepts options such as `--backend zellij`, `--layout vertical` (top/bottom), and `--editor 'nvim -u NONE'`. A setup update can change those preferences while preserving the managed integration.

## Uninstall

Ask the setup skill to uninstall, or run the installed management script:

```sh
python3 "${XDG_DATA_HOME:-$HOME/.local/share}/codex-split-editor/setup.py" uninstall
```

The script removes only the exact integration and runtime files it owns. It preserves other files and stops if an owned file was edited. Remove the plugin separately if desired:

```sh
codex plugin remove codex-split-editor@codex-split-editor
codex plugin marketplace remove codex-split-editor
```

## Development

Run tests with `python3 -m unittest discover -s tests`. CI covers Python 3.10 and 3.13 on Ubuntu, Python 3.13 on macOS, and a pinned Zellij integration run. Pull requests require the aggregate **CI** check; review approval is optional.

To prepare a release, run the **Release** workflow from `main` with a `vMAJOR.MINOR.PATCH` version. Dry run is enabled by default; it validates, tests, packages, and uploads an artifact without creating a tag or release.

## License

MIT. See [LICENSE](LICENSE).
