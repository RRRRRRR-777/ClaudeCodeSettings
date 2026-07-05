---
name: git-worktree
description: git worktreeで独立ブランチを切り出す。「worktreeで」「別ブランチで切り出して」で使用。
---

# git worktree 運用手順

別ブランチで作業中に、独立した修正を別ブランチで切り出す場合に使う。

## 手順

### 1. worktree 作成

```bash
git fetch origin main
git worktree add <パス> -b <ブランチ名> origin/main
```

`<ブランチ名>` は下の命名表に従う（チケットありは `ticket/<番号>-<機能名>`、チケットなしは `chore/<機能名>` 等）。

| 対象 | 命名 | 例 |
|------|------|-----|
| ブランチ名（チケットあり） | `ticket/<番号>-<機能名>` | `ticket/123-user-auth` |
| ブランチ名（チケットなし） | `chore/<機能名>` 等の慣用プレフィックス | `chore/fix-docs` |
| worktreeパス | 現リポジトリと同階層に、ブランチ名の `/` を `-` に置換して `<リポジトリ名>-` を前置 | `myrepo-ticket-123-user-auth` / `myrepo-chore-fix-docs` |

- 機能名まで含めた固有名にする（並列作業時の誤介入を防ぐため。`impl` 等の汎用接尾辞は使わず作業内容を表す名前にする）
- 現ブランチのまま実行可能（git switch 不要）

### 2. 変更の適用

#### 現ブランチに修正済みファイルがある場合

1. worktree側の対象ファイルに **Edit で必要な変更のみ**適用する
2. 現ブランチ側は `git checkout -- <対象ファイル>` で復元する

ファイルコピー（cp）は禁止。他ブランチの差分が混入するため。

#### 修正前の場合

worktree内で直接作業する。

### 3. コミット & PR

worktree内で commit → push → PR作成。通常のコミットフローに従う。

### 4. 後片付け（マージ後）

```bash
git worktree remove <パス>
```
