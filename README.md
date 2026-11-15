# codex-split-editor

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

Run tests with `python3 -m unittest discover -s tests`. The tmux integration smoke test uses a private temporary server; the Zellij integration smoke test is enabled when run from inside a Zellij pane.

## License

MIT. See [LICENSE](LICENSE).

---

# codex-split-editor (日本語)

Codex CLI を tmux または Zellij で起動し、外部エディターを隣のペインで開きます。既定のバックエンドは tmux です。Codex はエディターを閉じるまで待機し、保存して終了すると Codex にフォーカスが戻ります。エディターの終了コードも Codex に返します。

## 必要なもの

- Python 3.10 以上
- Codex CLI
- tmux（既定）または Zellij
- `nano`、`vim`、`nvim` などのエディター

多重化ツールは利用者がインストールしてください。このツールはソフトウェアを自動インストールせず、シェルの起動設定も変更しません。
Zellij を使う場合は、ペイン制御コマンドを備えた 0.46 以降が必要です。

## インストール

```sh
git clone https://github.com/takashiAg/codex-split-editor.git
cd codex-split-editor
mkdir -p ~/.local/bin
ln -s "$PWD/codex-split" "$HOME/.local/bin/codex-split"
ln -s "$PWD/codex-split-editor" "$HOME/.local/bin/codex-split-editor"
```

`~/.local/bin` を `PATH` に追加したうえで、次のように起動します。

macOS では、利用するバックエンドを `brew install tmux` または `brew install zellij` でインストールします。Zellij は 0.46 以降が必要です。

```sh
codex-split
codex-split --editor vim
codex-split --backend zellij --editor nvim
codex-split --layout vertical -- resume
```

`horizontal` は左右、`vertical` は上下分割です。`--editor` には引数を含められます。既定のエディターは `nano` です。`CODEX_SPLIT_EDITOR`、`CODEX_SPLIT_BACKEND`、`CODEX_SPLIT_LAYOUT` でも既定値を指定できます。

選択した tmux または Zellij 内で起動すると、既存セッション内で Codex を実行します。外から起動すると新しいセッションを作成します。新しい Zellij セッションではセッション限定の一時設定を使い、初回案内を隠して Ctrl+G を Codex に渡します。Zellij のロック切替は Ctrl+Alt+G です。既存 Zellij セッションの設定は変更しないため、Ctrl+G がロック切替に使われている場合は、そのセッションでキーを変更してください。すでに多重化ツールの外で起動した Codex ではなく、このランチャーから Codex を起動してください。

Codex で **Ctrl+G** を押すとエディターが開きます。nano では **Ctrl+O**、**Enter**、**Ctrl+X** の順に押して保存・終了します。Vim では `:wq` で保存して終了します。

## 削除

2 つのシンボリックリンクを削除し、必要なら複製したリポジトリも削除します。

```sh
rm "$HOME/.local/bin/codex-split" "$HOME/.local/bin/codex-split-editor"
rm -rf /path/to/codex-split-editor
```
