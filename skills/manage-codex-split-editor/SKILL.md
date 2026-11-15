---
name: manage-codex-split-editor
description: Set up, configure, or uninstall the Codex split editor on macOS when the user asks.
---

Use this skill only for setup, configuration, or removal of this local Codex integration.

## Setup

When the user asks to set up the integration, use the absolute path to this
`SKILL.md` provided by the loaded skill context. The plugin root is two
directories above `skills/manage-codex-split-editor/SKILL.md`. Run:

```sh
python3 "<absolute-plugin-root>/scripts/setup.py" setup --source "<absolute-plugin-root>"
```

Setup defaults to tmux, a left/right split, and `nano`; it does not install packages unless the user asks. The user can choose `--backend zellij`, `--layout vertical`, `--editor 'vim'`, or add `--install-deps` to install only missing selected tools with Homebrew. The script detects `SHELL`; pass `--shell fish`, `--shell zsh`, or `--shell bash` if that differs from the shell the user wants configured.

Setup installs a shell function that starts the normal Codex CLI in the selected multiplexer for interactive `codex` and `codex resume` sessions. It leaves noninteractive and administrative Codex commands on the original executable path. It configures `VISUAL` only for those Codex processes and does not change `EDITOR` or the user's global `VISUAL` setting. A fresh terminal is required once after setup so the shell function is loaded. In fish, the new function autoloads, but an existing shell may have cached a previous lookup.

## Uninstall

When the user asks to remove the setup, run:

```sh
python3 "<absolute-plugin-root>/scripts/setup.py" uninstall
```

The uninstaller removes only the exact shell function or marked shell startup block and runtime files recorded by setup. If a user edited that integration, it stops and preserves the changed file. The plugin remains installed; tell the user how to remove it with `codex plugin remove` only if they also ask to uninstall the plugin.

## Editing a prompt

After setup and a fresh terminal, the user can launch Codex with the usual `codex` or `codex resume` command. In the composer, Ctrl+G opens the read-only scrollable snapshot of the caller pane beside the editor. The snapshot is frozen at the moment editing starts; page with PgUp/PgDn and press `q` to return focus to the editor. The snapshot contains terminal scrollback available in that pane, not the full saved Codex conversation. Save and close the editor to return the draft to the Codex composer; the user reviews and sends it manually.
