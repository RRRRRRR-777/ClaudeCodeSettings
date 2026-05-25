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
git worktree add <パス> -b ticket/<番号> origin/main
```

- `<パス>` は現リポジトリと同階層に `<リポジトリ名>-ticket-<番号>` で作成する
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
