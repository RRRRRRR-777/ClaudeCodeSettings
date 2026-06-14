---
name: codex-review
description: Codex によるコードレビュー。設計/実装レビュー時に必ず呼ぶ。またそれらに自信がないときも読んでいいよ
---

# Codex Review Skill

OpenAI Codex CLI を Agent tool（バックグラウンド）で並列実行し、4ペルソナでコードレビューを行う。各ペルソナが焦点を1つに絞ることで出力が短く鋭くなり、重複も減る。Codex 処理中もユーザーと会話を継続できる。

## 手順

STEP 1 → STEP 5 を上から順に実行する。判断材料は各 STEP に書いてあるので、それ以外を考えなくてよい。

### STEP 1: レビュー対象を決める

codex CLI v0.130.0 では scope フラグ（`--uncommitted` / `--base` / `--commit`）と `[PROMPT]` が**併用できない**（`error: the argument '--uncommitted' cannot be used with '[PROMPT]'`）。ペルソナ prompt を渡す本 skill では scope フラグを使えないため、**scope は作業ツリーの状態で制御する**。

| 対象 | やり方 |
|------|--------|
| 未コミット変更（既定・主用途） | そのまま実行する。scope フラグ無しの `codex review -` は未コミット差分（staged/unstaged/untracked）を既定でレビューする |
| ブランチ差分 / 特定コミット | scope フラグと prompt は両立不可。以下のいずれかで対応する：<br>① ペルソナ無しで `codex review --base main`（焦点なしの汎用1本）<br>② 対象差分を未コミット状態へ戻して（例: `git reset --soft main`）既定スコープで実行 |

本プロジェクトの codex-review はコミット前（未コミット差分）に走るため、主経路は既定スコープで完結する。

### STEP 2: 差分の機械的フィルタリング（論理ゼロ差分の早期スキップ）

`git diff --name-only HEAD` で対象ファイルを列挙し、以下の除外パターンに**該当しないファイル（= 論理を含むファイル）が 1 件もない**場合、codex 起動を完全スキップして STEP 5 に進む（「除外のみで構成された PR」を判定するため。例: lock ファイルだけ、README タイポだけ）。1 件でもあれば STEP 3 に進む。

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
# 残ゼロなら codex 起動なしで STEP 5 へ
```

なお codex CLI は scope フラグと prompt が併用不可で物理的な per-file 除外ができないため、STEP 3 に進む場合 codex は除外対象も含む全差分を読む。除外対象への**指摘抑制**はペルソナ prompt 側で実施する（後述）。

### STEP 3: 4ペルソナを並列発行する
**1メッセージ**で4つの Agent を `run_in_background=true` で同時発行する。各 Agent の prompt は後方「ペルソナ定義」の**完成コマンド（heredoc）をそのまま貼る**だけ（役割・effort・焦点は確定済み。考えて編集しない）。
ペルソナ prompt は位置引数ではなく `-`（stdin）で渡す（scope フラグと併用不可なため、かつ長文を安全に渡すため）。ペルソナ定義は後述する。

- `codex-architect`
- `codex-code-review`
- `codex-security`
- `codex-qa`

> effort はペルソナごとに確定済み（architect/security=high、code-review/qa=medium）。重大リリース直前の総点検時のみ、全ペルソナを `high` に上げてよい。

### STEP 4: 全完了を待つ
4体すべての完了通知が揃うまで待つ。その間ユーザーとの会話は継続してよい。

### STEP 5: 統合報告する
4体の stdout を統合し、後方「報告フォーマット」に流し込む。並べ方のルール:

1. **重要度順**（Must → Should → Nit）。各指摘に発信ペルソナ名を付記
2. **複数ペルソナが同じ箇所を指摘した点を最優先**に置く
3. ペルソナ間で意見が衝突する箇所（例: コードレビュアー「厳密に」 vs アーキテクト「作りすぎ」）は明示する

STEP 2 で codex 起動をスキップした場合、本文の先頭に「**codex 起動なし: 差分が論理ゼロ（除外対象のみ）のため**」と除外内訳を 1 行で明記して完了する。

---

## ペルソナ定義（STEP 3 で貼る素材）

各ブロックの heredoc コマンドを Agent prompt の本文として使う。scope フラグは付けない（STEP 1 参照。未コミット差分が既定でレビューされる）。Agent への指示は共通で「Bashツールで以下のコマンドを実行（timeout: 600000）。結果のstdoutをそのまま返す」。

各ペルソナ prompt 末尾には**共通の指摘抑制ルール**（後述「指摘抑制ルール」セクション参照）が含まれる。これは「lock / 自動生成 / vendor 等への指摘」「lint/typecheck/go vet で機械検出される類の指摘」を出力しないためのもの（重複排除・無価値指摘排除）。

### codex-architect（effort: high）
```
codex review -c model_reasoning_effort="high" - <<'PROMPT'
あなたはアーキテクトです。次の観点【だけ】でレビューしてください。他観点（コード品質・セキュリティ・テスト）は他者が見るので触れないこと。各指摘に重要度(Must/Should/Nit)を付け、2-3行以内で簡潔に。
焦点:
- 設計書との整合: 実装が feature-spec / system-design と一致するか。設計書にない挙動・エンドポイント・データフローの勝手な追加がないか。openapi.yaml とレスポンスの整合。設計意図を壊していないか
- 責務分離: handler/usecase/repository の責務混在。ビジネスロジックの層漏れ。単一責任違反
- 依存関係: 依存方向の逆流・循環依存。具象でなくインターフェースへの依存(DI)。外部ライブラリ依存の抽象化
- 拡張性・凝集度: 「作りすぎない」原則に反する過剰抽象。将来拡張を壊す密結合。設定値・定数のハードコード散在
- 一貫性: 既存同種実装とのパターン不一致。重複実装（既存ユーティリティの再発明）

指摘抑制ルール（必ず守ること）:
- 次のファイル種別に対する指摘は差分にあっても出力しない（観点ゼロ・自動生成のため）: lock ファイル（package-lock.json / pnpm-lock.yaml / yarn.lock / go.sum）/ スナップショット（*.snap / __snapshots__/）/ ビルド成果物（dist / build / *.min.js / *.map）/ vendor / node_modules / 先頭に Code generated / DO NOT EDIT / @generated を含むファイル / testdata 配下のデータファイル
- 次の指摘は出力しない（lint / typecheck / go vet / eslint で機械検出されるため重複）: フォーマット崩れ・未使用変数/未使用import・型エラー・命名規則のうち linter で検出されるもの
PROMPT
```

### codex-code-review（effort: medium）
```
codex review -c model_reasoning_effort="medium" - <<'PROMPT'
あなたはコードレビュアーです。次の観点【だけ】でレビューしてください。他観点（設計・セキュリティ・テスト）は他者が見るので触れないこと。各指摘に重要度(Must/Should/Nit)を付け、2-3行以内で簡潔に。
焦点:
- 正しさ・バグ: ロジック誤り・オフバイワン・分岐漏れ。nil/ゼロ値/空配列の扱い。境界・オーバーフロー・型変換。異常系の処理漏れ
- エラーハンドリング: 握り潰し（無視・ログだけ）。ラップ/コンテキスト付与。panic/throw 濫用。リトライ・フォールバックの要否
- 可読性・保守性: 命名が意図を表すか。関数長・ネスト深さ。マジックナンバー/文字列。経緯コメント混入（禁止）。デッドコード・未使用変数/import
- 言語規約準拠: go-standards / frontend.md の idiom。命名・フォーマット。any/interface{} の濫用
- 並行処理: 共有リソースの排他制御(mutex/channel/atomic)。競合・デッドロック。goroutine/Promise リーク
- リソース管理: ファイル/コネクション/コンテキストの close 漏れ。defer の適切な使用

指摘抑制ルール（必ず守ること）:
- 次のファイル種別に対する指摘は差分にあっても出力しない（観点ゼロ・自動生成のため）: lock ファイル（package-lock.json / pnpm-lock.yaml / yarn.lock / go.sum）/ スナップショット（*.snap / __snapshots__/）/ ビルド成果物（dist / build / *.min.js / *.map）/ vendor / node_modules / 先頭に Code generated / DO NOT EDIT / @generated を含むファイル / testdata 配下のデータファイル
- 次の指摘は出力しない（lint / typecheck / go vet / eslint で機械検出されるため重複）: フォーマット崩れ・未使用変数/未使用import・型エラー・命名規則のうち linter で検出されるもの
PROMPT
```

### codex-security（effort: high）
```
codex review -c model_reasoning_effort="high" - <<'PROMPT'
あなたはセキュリティレビュアーです。次の観点【だけ】でレビューしてください。他観点（設計・コード品質・テスト）は他者が見るので触れないこと。各指摘に重要度(Must/Should/Nit)を付け、2-3行以内で簡潔に。
焦点:
- 入力・インジェクション: SQLi（プレースホルダ）・XSS（エスケープ/dangerouslySetInnerHTML）・コマンドインジェクション・パストラバーサル。入力バリデーション欠如
- 認証・認可: 認証チェック漏れ。認可（自分/他人のリソース）検証。IDOR。セッション/トークンの扱い
- 機密情報: 秘密情報のハードコード。ログ/レスポンスへの漏洩。.env と .env.sample の同期。エラーからの内部情報露出
- 通信・データ保護: HTTPS/TLS 前提。CORS 妥当性。暗号化/ハッシュ化（パスワード平文保存等）
- 外部連携・制約: レート制限/クォータ考慮。外部レスポンスの検証。依存ライブラリの既知脆弱性
- その他: CSRF 対策。過剰な権限付与。監査ログの要否

指摘抑制ルール（必ず守ること）:
- 次のファイル種別に対する指摘は差分にあっても出力しない（観点ゼロ・自動生成のため）: lock ファイル（package-lock.json / pnpm-lock.yaml / yarn.lock / go.sum）/ スナップショット（*.snap / __snapshots__/）/ ビルド成果物（dist / build / *.min.js / *.map）/ vendor / node_modules / 先頭に Code generated / DO NOT EDIT / @generated を含むファイル / testdata 配下のデータファイル
- 次の指摘は出力しない（lint / typecheck / go vet / eslint で機械検出されるため重複）: フォーマット崩れ・未使用変数/未使用import・型エラー・命名規則のうち linter で検出されるもの
PROMPT
```

### codex-qa（effort: medium）
```
codex review -c model_reasoning_effort="medium" - <<'PROMPT'
あなたはQA/テスターです。次の観点【だけ】でレビューしてください。他観点（設計・コード品質・セキュリティ）は他者が見るので触れないこと。各指摘に重要度(Must/Should/Nit)を付け、2-3行以内で簡潔に。
焦点:
- テスト網羅: 新規ファイルに対応テストがあるか（BE: usecase/handler, FE: コンポーネント/APIクライアント）。BE/FE 両方にあるか。正常系だけでなく異常系・エラーパスをカバーしているか
- テスト技法: 境界値分析（最小・最大・境界±1・空・0）。同値分割。デシジョンテーブル（条件組み合わせ）。状態遷移の網羅
- テストの質: アサーションが意味ある検証か（実行するだけになっていないか）。実装の写し（トートロジー）になっていないか。過剰モックで実質テストしていないか。テストの独立性（順序依存・共有状態）
- E2E・シナリオ: test_scenarios.md に対応シナリオの追加・更新があるか。ハッピーパスの E2E カバレッジ
- 回帰・副作用: 既存テストを壊していないか。カバレッジ低下。フレーキー（時刻・乱数・非同期待ち）

指摘抑制ルール（必ず守ること）:
- 次のファイル種別に対する指摘は差分にあっても出力しない（観点ゼロ・自動生成のため）: lock ファイル（package-lock.json / pnpm-lock.yaml / yarn.lock / go.sum）/ スナップショット（*.snap / __snapshots__/）/ ビルド成果物（dist / build / *.min.js / *.map）/ vendor / node_modules / 先頭に Code generated / DO NOT EDIT / @generated を含むファイル / testdata 配下のデータファイル
- 次の指摘は出力しない（lint / typecheck / go vet / eslint で機械検出されるため重複）: フォーマット崩れ・未使用変数/未使用import・型エラー・命名規則のうち linter で検出されるもの
PROMPT
```

## 報告フォーマット（STEP 5 で使う素材）

| 重要度 | 指摘 | 発信ペルソナ | 対象 |
|--------|------|------------|------|
| Must | ... | セキュリティ | file:line |
| Should | ... | アーキテクト, コード | file:line |
