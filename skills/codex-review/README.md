# Codex Review Skill

Claude CodeからOpenAI Codex CLIをAgent toolでバックグラウンド実行し、コードレビュー・デバッグを行うSkillです。

## 前提条件

### Codex CLIのインストール
```bash
brew install openai-codex
```

※ Warpやアクセシビリティ権限は不要です。

## 使い方

### 1. レビュー内容を指定
```
「codexでレビューして」
「/codex-review」
```

→ Claude Codeが以下を確認します：
- タスク種別（レビュー / デバッグ / 両方）
- 対象（現在の変更、特定ファイル、特定ブランチ）
- 観点（セキュリティ、パフォーマンス、アーキテクチャ、全体）

### 2. 自動実行・結果報告
Agent toolがCodex CLIをバックグラウンドで実行します。
処理中もClaude Codeとの会話を継続できます。
完了後、結果が構造化されて自動的に報告されます。

## 並列実行パターン

複数の観点を同時にレビューできます：

| パターン | 説明 |
|---------|------|
| 単一レビュー | 1つのAgent でレビュー実行 |
| 複数観点レビュー | セキュリティ + パフォーマンス等を並列実行 |
| レビュー + デバッグ | レビューとデバッグを同時に並列実行 |

## ファイル構成

```
~/.claude/skills/codex-review/
├── SKILL.md   # Skill定義
└── README.md  # 開発者向けドキュメント
```

## トラブルシューティング

### Codex CLIの認証エラー
```
Error: Authentication failed
```
→ `codex auth` を実行してOpenAI APIキーを設定してください

### タイムアウト（10分超過）
→ レビュー対象を絞る（特定ファイル指定、観点を限定）か、`codex review --commit SHA` で特定コミットに限定してください

### Codex CLIが見つからない
```
command not found: codex
```
→ `brew install openai-codex` でインストールしてください
