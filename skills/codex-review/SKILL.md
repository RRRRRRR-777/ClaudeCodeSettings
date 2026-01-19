---
name: codex-review
description: Codexを使用したコードレビュー。Warp分割ペインでCodexを起動し、実装や設計のレビューを依頼します。
---

# Codex Review Skill

## 概要
OpenAI Codex CLIを使用してコードレビューを実行します。
Warpの分割ペインでCodexを起動し、リアルタイムでレビュー内容を観測できます。

## トリガー
以下のキーワードで呼び出されます：
- `codex`、`協業`、`レビュー`
- `/codex-review`

## Codex CLIコマンド

```bash
# インタラクティブモード（デフォルト・対話形式で継続可能）
codex "現在のgit diffをレビューしてください"

# 非インタラクティブモード（結果を出力して終了）
codex review --uncommitted
```

## 実行手順

### 1. ユーザーに確認する
まず以下を確認します：
- **レビュー対象**: 現在の変更(git diff)、特定ファイル、特定ブランチなど
- **レビュー観点**: セキュリティ、パフォーマンス、アーキテクチャ、全体、指定なし
- **その他**: 特に確認してほしい点があれば

### 2. Codexを起動
ユーザーの回答をまとめて、Warpの分割ペインでCodexを起動します。

ログファイル: `./tmp/codex-review.log`
結果ファイル: `./tmp/codex-result.txt`

```bash
osascript <<'EOF'
set the clipboard to "script -q ./tmp/codex-review.log codex \"{ユーザーの回答に基づいたレビュー依頼文}。レビュー完了時に以下の内容を ./tmp/codex-result.txt に保存してください：
## Findings
（問題点があれば）

## Open Questions
（質問事項があれば）

## 提案
（改善案があれば）

## 結論
（全体の結論）\""

tell application "Warp" to activate
delay 0.5
tell application "System Events"
    tell process "Warp"
        keystroke "d" using command down
        delay 0.8
        keystroke "v" using command down
        delay 0.3
        key code 36
    end tell
end tell
EOF
```

### 3. レビュー結果の取得
ユーザーが「レビュー完了」「結果を確認して」などと伝えたら、結果ファイルを読み取ります。

```bash
cat ./tmp/codex-result.txt 2>/dev/null || echo "結果ファイルが見つかりません。Codexセッションでレビューを完了してください"
```

## codex review オプション

| オプション | 説明 |
|-----------|------|
| `--uncommitted` | 未コミットの変更をレビュー |
| `--base <BRANCH>` | 指定ブランチとの差分をレビュー |
| `--commit <SHA>` | 特定コミットをレビュー |
| `-m, --model <MODEL>` | 使用モデルを指定 |

## 観点別プロンプト例

- **セキュリティ**: `"セキュリティ観点でレビュー。インジェクション脆弱性、認証・認可の不備に注意"`
- **アーキテクチャ**: `"設計観点でレビュー。責務の分離、依存関係の方向性に注意"`
- **パフォーマンス**: `"パフォーマンス観点でレビュー。N+1問題、メモリリークに注意"`
