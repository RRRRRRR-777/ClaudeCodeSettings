# browser-use CLI Skill

browser-use CLIを使ったブラウザ手動操作スキル。APIキー不要。

## 前提

- `browser-use` コマンドはエイリアスとして登録済み（`~/.zshrc.alias`）
- どのディレクトリからでも実行可能
- `--headed` を付けるとブラウザウィンドウを表示

## ワークフロー

1. `browser-use state` でページ状態と要素一覧（`[index]`付き）を取得
2. indexを使って `click`, `input`, `select` 等で操作
3. 操作後に再度 `state` で結果を確認

## コマンドリファレンス

### セッション管理

| コマンド | 説明 |
|---------|------|
| `browser-use sessions` | アクティブなセッション一覧 |
| `browser-use close` | 現在のセッションを閉じる |
| `browser-use close --all` | 全セッションを閉じる |

### ナビゲーション

| コマンド | 説明 |
|---------|------|
| `browser-use open <url>` | URLを開く |
| `browser-use back` | 前のページに戻る |
| `browser-use state` | 現在のページ状態を取得（URL・タイトル・要素一覧） |

### 要素操作

| コマンド | 説明 |
|---------|------|
| `browser-use click <index>` | 要素をクリック（座標 `x y` も可） |
| `browser-use dblclick <index>` | ダブルクリック |
| `browser-use rightclick <index>` | 右クリック |
| `browser-use hover <index>` | ホバー |
| `browser-use input <index> "<text>"` | 特定要素にテキスト入力 |
| `browser-use select <index> "<value>"` | ドロップダウンの選択 |

### テキスト・キー入力

| コマンド | 説明 |
|---------|------|
| `browser-use type "<text>"` | テキストを入力（フォーカス中の要素に） |
| `browser-use keys "<key>"` | キー送信（例: `Enter`, `Control+a`, `Tab`） |

### スクロール

| コマンド | 説明 |
|---------|------|
| `browser-use scroll down` | 下にスクロール |
| `browser-use scroll up` | 上にスクロール |
| `browser-use scroll down --amount 500` | ピクセル指定でスクロール |

### タブ操作

| コマンド | 説明 |
|---------|------|
| `browser-use switch <tab_index>` | タブを切り替え |
| `browser-use close-tab` | 現在のタブを閉じる |
| `browser-use close-tab <tab_index>` | 指定タブを閉じる |

### 情報取得

| コマンド | 説明 |
|---------|------|
| `browser-use get title` | ページタイトル |
| `browser-use get html` | ページHTML |
| `browser-use get text` | ページテキスト |
| `browser-use get value <index>` | input要素の値 |
| `browser-use get attributes <index>` | 要素の属性 |
| `browser-use get bbox <index>` | 要素のバウンディングボックス |

### スクリーンショット

| コマンド | 説明 |
|---------|------|
| `browser-use screenshot <path>` | スクリーンショット保存 |
| `browser-use screenshot --full <path>` | フルページスクリーンショット |

### Cookie操作

| コマンド | 説明 |
|---------|------|
| `browser-use cookies get` | 全Cookie取得 |
| `browser-use cookies set` | Cookie設定 |
| `browser-use cookies clear` | Cookie削除 |
| `browser-use cookies export <file>` | JSONエクスポート |
| `browser-use cookies import <file>` | JSONインポート |

### 待機

| コマンド | 説明 |
|---------|------|
| `browser-use wait selector "<css>"` | CSSセレクタの出現を待つ |
| `browser-use wait text "<text>"` | テキストの出現を待つ |

### JavaScript実行

| コマンド | 説明 |
|---------|------|
| `browser-use eval "<js>"` | JavaScriptを実行 |

## グローバルオプション

| オプション | 説明 |
|-----------|------|
| `--headed` | ブラウザウィンドウを表示 |
| `-s <name>` | セッション名を指定（デフォルト: `default`） |
| `-b {chromium,real,remote}` | ブラウザモードを指定 |
| `--json` | JSON形式で出力 |

## 操作の流れの例

```bash
# 1. ページを開く
browser-use --headed open https://example.com

# 2. 状態を確認（要素のindexを取得）
browser-use state

# 3. 要素をクリック（stateで確認した[24]のリンク等）
browser-use click 24

# 4. フォームに入力
browser-use input 5 "検索ワード"

# 5. Enterキーを送信
browser-use keys Enter

# 6. スクリーンショットを撮る
browser-use screenshot result.png

# 7. セッションを閉じる
browser-use close
```
