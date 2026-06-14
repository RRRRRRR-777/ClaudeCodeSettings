---
name: claude-review
description: Claude による独立コンテキストでの 4 ペルソナ並列コードレビュー。設計/実装レビュー時の補強として使う。codex-review と独立運用
---

# Claude Review Skill

Claude を Agent tool（バックグラウンド・新規コンテキスト）で並列実行し、4 ペルソナでコードレビューを行う。codex-review と同じ構造だが、実行手段が Claude サブエージェントである点が異なる。各ペルソナは**メインセッションの会話履歴を一切引き継がない独立コンテキスト**で動く（フレッシュコンテキスト保証）。

## 構成

| ペルソナ | subagent_type | model | effort | 備考 |
|---------|---------------|-------|--------|------|
| アーキテクト | `claude-architect` | opus | xhigh | prompt 内に `ultrathink` 含む（ターン限定で最深推論）|
| セキュリティ | `claude-security` | opus | xhigh | |
| コード | `claude-code-review` | opus | xhigh | |
| QA | `claude-qa` | opus | high | Sonnet では xhigh→high にフォールバックされるため Opus high で明示 |

各ペルソナの観点・指摘抑制ルールは subagent 定義側（`~/.claude/agents/claude-*.md`）に書いてある。本 skill では起動と統合のみ扱う。

## 手順

STEP 1 → STEP 5 を上から順に実行する。判断材料は各 STEP に書いてあるので、それ以外を考えなくてよい。

### STEP 1: レビュー対象を決める

未コミット差分（既定）をレビューする。`git diff HEAD` が示す差分が対象（staged / unstaged / 新規追跡ファイル含む）。

ブランチ差分や特定コミットを対象にする場合は、対象差分を未コミット状態へ戻して（例: `git reset --soft main`）から本 skill を実行する。

### STEP 2: 差分の機械的フィルタリング（論理ゼロ差分の早期スキップ）

`git diff --name-only HEAD` で対象ファイルを列挙し、以下の除外パターンに**該当しないファイル（= 論理を含むファイル）が 1 件もない**場合、Claude サブエージェント起動を完全スキップして STEP 5 に進む（「除外のみで構成された PR」を判定するため。例: lock ファイルだけ、README タイポだけ）。1 件でもあれば STEP 3 に進む。

| 除外対象 | パターン例 | 理由 |
|----------|-----------|------|
| ロックファイル | `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` / `go.sum` | 自動生成・観点ゼロ |
| スナップショット | `*.snap` / `**/__snapshots__/**` | テスト出力 |
| ビルド成果物 | `dist/**` / `build/**` / `*.min.js` / `*.map` | コンパイル出力 |
| 第三者コード | `vendor/**` / `node_modules/**` | レビュー対象外 |
| 自動生成ファイル | 先頭 5 行に `Code generated` / `DO NOT EDIT` / `@generated` を含む | go generate / openapi-codegen 等 |
| テストフィクスチャ | `**/testdata/**` の `*.json` / `*.yaml` | データのみ |

判定例:
```bash
git diff --name-only HEAD \
  | grep -vE '(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|go\.sum)$' \
  | grep -vE '(\.snap$|/__snapshots__/|^(dist|build|vendor|node_modules)/|\.min\.js$|\.map$)' \
  | grep -vE '/testdata/.*\.(json|ya?ml)$'
# 残ゼロなら Claude 起動なしで STEP 5 へ
```

なお Claude サブエージェントは subagent 側の指摘抑制ルールによって、除外対象ファイルへの指摘を出力しない設計になっている。STEP 2 のスキップは「**そもそも起動する価値がない PR**」を弾くためのもの。

### STEP 3: 4ペルソナを並列発行する

**1メッセージ**で 4 つの Agent を `run_in_background=true` で同時発行する。各ペルソナは独立した subagent として `~/.claude/agents/` 配下に定義済み。Agent 呼び出し時は以下を指定する:

| 引数 | 値 |
|------|----|
| `subagent_type` | `claude-architect` / `claude-security` / `claude-code-review` / `claude-qa` |
| `description` | 3-5語の短い説明（例: "architect review"） |
| `prompt` | 下記の共通テンプレート |
| `run_in_background` | `true` |

共通 prompt テンプレート（4 体すべてに同じ文を渡す。観点は subagent 定義側に書いてあるため再掲しない）:
```
git diff HEAD で取得した未コミット差分を、自分の subagent 定義に書かれた観点と指摘抑制ルールに従ってレビューせよ。出力はレビュー本文のみ（前置き不要）。指摘がない場合は「指摘なし」と1行返す。
```

> モデル・effort はそれぞれの subagent frontmatter で確定済み。Agent 呼び出し時に `model` パラメータで上書きしないこと（架構を崩す）。

### STEP 4: 全完了を待つ

4 体すべての完了通知が揃うまで待つ。その間ユーザーとの会話は継続してよい。

### STEP 5: 統合報告する

4 体の最終出力を統合し、後方「報告フォーマット」に流し込む。並べ方のルール:

1. **重要度順**（Must → Should → Nit）。各指摘に発信ペルソナ名を付記
2. **複数ペルソナが同じ箇所を指摘した点を最優先**に置く
3. ペルソナ間で意見が衝突する箇所（例: コード「厳密に」 vs アーキテクト「作りすぎ」）は明示する

STEP 2 で Claude 起動をスキップした場合、本文の先頭に「**Claude 起動なし: 差分が論理ゼロ（除外対象のみ）のため**」と除外内訳を 1 行で明記して完了する。

---

## 報告フォーマット（STEP 5 で使う素材）

| 重要度 | 指摘 | 発信ペルソナ | 対象 |
|--------|------|------------|------|
| Must | ... | セキュリティ | file:line |
| Should | ... | アーキテクト, コード | file:line |
| Nit | ... | QA | file:line |
