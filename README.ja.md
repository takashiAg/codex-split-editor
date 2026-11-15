# Codex Split Editor（日本語）

[English](README.md)

Codex のプロンプトを隣のターミナルペインで編集する Codex プラグインです。プラグインをインストールして一度セットアップすれば、通常の `codex` と `codex resume` を使えます。入力欄で **Ctrl+G** を押すと設定したエディターが開きます。保存して閉じると編集した文章が Codex に戻り、内容を確認して自分で送信できます。

macOS に対応しています。Codex の外部エディター処理中、現在のやり取りは一時停止します。編集画面の隣には呼び出し元ペインのスクロールバックを読み取り専用のスナップショットとして表示します。保存された会話全体ではありません。プロンプトを自動送信しません。

## インストール

Codex でこのリポジトリをローカルマーケットプレイスとして追加し、プラグインをインストールします。

```text
codex plugin marketplace add takashiAg/codex-split-editor
codex plugin add codex-split-editor@codex-split-editor
```

Codex が案内するセットアップスキルを使うか、Codex に Codex Split Editor のセットアップを依頼してください。セットアップにより、小さなシェル関数が追加されます。対話的な `codex` と `codex resume` は選択した多重化ツール内で起動します。関数を読み込むため、一度新しいターミナルを開いてください。

既定値は tmux、左右分割、`nano` です。セットアップ時に Zellij、上下分割、別のエディターを選べます。`EDITOR`、グローバルな `VISUAL`、無関係なシェル設定、既存の多重化セッションは変更しません。依存ソフトは依頼がない限りインストールしません。

チェックアウトから直接セットアップする場合は Python 3.10 以上が必要です。pnpm は任意です。

```sh
python3 scripts/setup.py setup --shell fish --backend tmux --layout horizontal --editor nano
# または
pnpm run setup -- --shell fish --backend zellij --editor vim
```

fish、zsh、bash に対応します。Codex を起動するシェルを選んでください。必要なコマンドがない場合は自分でインストールするか、`--install-deps` を明示して Homebrew から選択した不足ツールだけをインストールできます。

## 使い方

Codex で **Ctrl+G** を押します。スナップショットは PgUp/PgDn と矢印キーで閲覧でき、`q` で閉じます。エディターは隣のペインにあります。nano では **Ctrl+O**、**Enter**、**Ctrl+X** の順に押して保存・終了します。Vim では `:wq` で保存して終了します。編集した文章が Codex の入力欄に戻るので、確認して送信してください。

既定のバックエンドは tmux です。Zellij は 0.46.0 以降が必要です。セットアップスキルで `--backend zellij`、`--layout vertical`（上下分割）、`--editor 'nvim -u NONE'` などを指定できます。セットアップを再実行して設定を変更できます。

## アンインストール

セットアップスキルに削除を依頼するか、インストール済みの管理スクリプトを実行します。

```sh
python3 "${XDG_DATA_HOME:-$HOME/.local/share}/codex-split-editor/setup.py" uninstall
```

自分が管理するシェル関数とランタイムファイルだけを削除します。他のファイルは保持し、管理対象が編集されている場合は停止します。必要ならプラグインも別途削除します。

```sh
codex plugin remove codex-split-editor@codex-split-editor
codex plugin marketplace remove codex-split-editor
```

## 開発

テストは `python3 -m unittest discover -s tests` で実行できます。CI は Ubuntu で Python 3.10 と 3.13、macOS で Python 3.13、固定した Zellij で統合テストを実行します。プルリクエストでは集約チェック **CI** が必須です。レビュー承認は任意です。

リリースを準備するには、`main` から **Release** ワークフローを実行し、`vMAJOR.MINOR.PATCH` 形式でバージョンを指定します。既定のドライランで検証・テスト・パッケージ化を行い、成果物をアップロードします。タグや Release は作成しません。

## ライセンス

MIT ライセンスです。[LICENSE](LICENSE) を参照してください。
