# Codex Review Skill

Claude CodeからOpenAI Codex CLIを呼び出してコードレビューを行うSkillです。

## 前提条件

### 1. Warpのインストール
https://www.warp.dev/

### 2. Codex CLIのインストール
```bash
brew install openai-codex
```

### 3. Warpのアクセシビリティ権限
システム環境設定 > プライバシーとセキュリティ > アクセシビリティ でWarpに権限を付与

## 使い方

### 1. レビュー内容を指定
```
「codexでレビューして」
「/codex-review」
```

→ Claude Codeが以下を確認します：
- レビュー対象（現在の変更、特定ファイル、特定ブランチ）
- レビュー観点（セキュリティ、パフォーマンス、アーキテクチャ、全体）
- その他確認してほしい点

### 2. Codexと対話
Warpの分割ペインでCodexが起動し、レビューが開始されます。
レビュー完了時にCodexが結果を `./tmp/codex-result.txt` に保存します。

### 3. 結果を確認
```
「レビュー完了」
「結果を確認して」
```

→ Claude Codeが結果ファイルを読み取って報告します

## ファイル構成

```
~/.claude/skills/codex-review/
├── SKILL.md   # Skill定義
└── README.md  # 開発者向けドキュメント
```

## ログ/結果ファイル

- `./tmp/codex-review.log` - Codexの対話ログ（毎回上書き）
- `./tmp/codex-result.txt` - レビュー結果（Codexが出力）

## トラブルシューティング

### osascriptでエラーが出る
```
execution error: osascriptにはキー操作の送信は許可されません。
```
→ Warpのアクセシビリティ権限を確認

### ペインは増えたがコマンドが入力されない
→ delayのタイミング問題。SKILL.mdのdelay値を増やす

### 結果ファイルが見つからない
→ Codexセッションでレビューを完了してください
