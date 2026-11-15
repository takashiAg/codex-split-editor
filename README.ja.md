# codex-split-editor（日本語）

[English](README.md)

Codex CLI を tmux または Zellij で起動し、外部エディターを隣のペインで開きます。既定のバックエンドは tmux です。Codex はエディターを閉じるまで待機し、保存して終了すると Codex にフォーカスが戻ります。エディターの終了コードも Codex に返します。

## 必要なもの

- Python 3.10 以上
- Codex CLI
- tmux（既定）または Zellij
- `nano`、`vim`、`nvim` などのエディター

macOS と Linux に対応しています。WSL では未検証です。

Zellij を使う場合は、ペイン制御コマンドを備えた 0.46 以降が必要です。macOS では `brew install tmux` または `brew install zellij` で必要なバックエンドをインストールしてください。

多重化ツールは利用者がインストールしてください。このツールはソフトウェアを自動インストールせず、シェルの起動設定も変更しません。

## インストール

```sh
git clone https://github.com/takashiAg/codex-split-editor.git
cd codex-split-editor
mkdir -p ~/.local/bin
ln -s "$PWD/codex-split" "$HOME/.local/bin/codex-split"
ln -s "$PWD/codex-split-editor" "$HOME/.local/bin/codex-split-editor"
```

`~/.local/bin` を `PATH` に追加したうえで、次のように起動します。fish では `fish_add_path ~/.local/bin` を実行します。

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

## 開発

テストは `python3 -m unittest discover -s tests` で実行できます。tmux の統合テストは専用の一時サーバーを使います。`tests/run_zellij_integration.sh` は Zellij 0.46.0 のバックグラウンドセッションで統合テストを実行し、タイムアウトやスキップも失敗として扱います。

## CI とリリース

プルリクエストと `main` への push で必須チェック `CI` が実行されます。Ubuntu では Python 3.10 と 3.13、macOS では Python 3.13 を検証し、固定バージョンの Zellij 0.46.0 でも統合テストを実行します。`main` は保護され、変更はプルリクエスト経由で CI 成功後に取り込まれます。レビューは任意で、承認数の必須設定はありません。

リリースを準備するには、`main` から **Release** ワークフローを実行し、`vMAJOR.MINOR.PATCH` 形式のバージョンを指定します。既定のドライランでは入力を検証し、CI を再実行して、配布アーカイブと SHA-256 ファイルを作成し、ワークフロー成果物として保存します。タグと GitHub Release を作成する準備ができたときだけドライランを無効にしてください。既存のタグや Release は上書きしません。

## ライセンス

MIT ライセンスです。[LICENSE](LICENSE) を参照してください。
