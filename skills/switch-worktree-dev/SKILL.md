---
name: switch-worktree-dev
description: 指定worktreeへローカルdev環境を切替する。現在起動しているサーバーを切り替えたいときに使う。
---

# switch-worktree-dev Skill

## 用途

別の worktree（`ticket/{番号}`）で開発を再開するときに、ローカル dev 環境（FE: `localhost:3000` / BE: `localhost:8080`）を切替するためのワンショット手順。

引数: 切替先 worktree のディレクトリ名（例: `ticket+254`、`ticket-253`）。省略時はユーザーに確認する。

## 実行手順

### Phase 1: 入力の確定

1. 引数で worktree ディレクトリ名を受け取る
2. 未指定なら `git worktree list` を実行し、結果を提示して `AskUserQuestion` で選ばせる
3. 切替先のフルパスを決定: `/Users/bokuyamada/RRRRRRR777/Repositories/SicouLab/.claude/worktrees/{worktree名}`
4. 切替先が存在するか `Glob` で確認する。なければ中止してユーザーに報告

### Phase 1.5: 切替先の整合性検査

切替先が「コードと UI/DB の認識がずれる」状態で起動して、表示崩れや事故を起こすのを防ぐ。**Phase 2 の dev サーバ停止前**に実施する。

#### 1.5a: worktree HEAD と origin の同期チェック

切替先 worktree のローカル HEAD が `origin/<同名ブランチ>` と diverged していないかを確認する。
diverged の場合、ローカルにあるはずのコミットが消えた、あるいはローカルが古いまま、のいずれかの可能性が高い。

```bash
git -C {WT} fetch origin {ブランチ名}
git -C {WT} status --porcelain=v2 --branch
git -C {WT} log --oneline -5
```

判定:
- `ahead 0, behind 0` → 通常、続行
- `behind` のみ → `git pull --ff-only` で取り込む
- `ahead N` のみで未 push のコミットがある → ユーザーに「未 push のコミットがある。push するか確認」
- diverged（ahead と behind 両方）→ **中止してユーザーに報告**。`git log --oneline -10` の差分を提示し、対処を仰ぐ。多くは worktree 再作成で復旧する:
  ```bash
  git -C {ROOT} worktree remove --force .claude/worktrees/{worktree名}
  git -C {ROOT} branch -D {ブランチ名}
  git -C {ROOT} fetch origin {ブランチ名}
  git -C {ROOT} worktree add {WT} -b {ブランチ名} origin/{ブランチ名}
  ```

#### 1.5b: DB seeds と現行 DB の整合性チェック

切替先 worktree の `backend/seeds/*.sql` と現行 DB の重要マスタ（`plans` 等）に差分がないかを確認する。
`ON CONFLICT (name) DO NOTHING` の seed は既存行を上書きしないため、「seed は新しいが DB は古い」状態になりやすい。

```bash
# 主要 seed の中身を確認
sed -n '1,30p' {WT}/backend/seeds/01_plans.sql

# DB 側の現状
docker exec sicoulab-postgres-1 psql -U postgres -d sicoulab_database_development \
  -c "SELECT name, tier, amount, currency, is_active FROM plans ORDER BY id;"
```

判定:
- seed の値と DB の値が一致 → 続行
- 差分あり（例: `amount` や `tier` がずれる）→ ユーザーに差分を提示し、`UPDATE` で揃える案を提案してから実行する
- seed に新規テーブルが追加されている場合 → `make -C {WT}/backend seed` の実行を提案する

これら検査で「中止」と判定された場合、Phase 2 以降には進まない。

### Phase 2: 既存 dev サーバの停止（PID ファイル管理）

`lsof -ti:PORT | xargs kill` は禁止（無関係プロセス巻き込みで Docker Desktop 等が落ちる前例あり）。PID ファイルで対象プロセスだけを停止する。

```bash
for f in /tmp/sicoulab-frontend.pid /tmp/sicoulab-backend.pid; do
  if [ -f "$f" ]; then
    pid=$(cat "$f")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && echo "stopped $f (pid=$pid)"
    fi
    rm -f "$f"
  fi
done
```

PID ファイルが無く、かつポートが埋まっている場合は、`ps -ef | grep -E "next dev|go run"` の結果をユーザーに提示して、kill 対象を**ユーザーに確定させてから**停止する。`lsof` での一括 kill は提案しない。

### Phase 3: .env シンボリックリンク張り直し

切替先 worktree の `frontend/.env` と `backend/.env` を、メインリポジトリの実体へ向けるシンボリックリンクで再作成する。

```bash
WT=/Users/bokuyamada/RRRRRRR777/Repositories/SicouLab/.claude/worktrees/{worktree名}
MAIN=/Users/bokuyamada/RRRRRRR777/Repositories/SicouLab

rm -f "$WT/frontend/.env" "$WT/backend/.env"
ln -s "$MAIN/frontend/.env" "$WT/frontend/.env"
ln -s "$MAIN/backend/.env" "$WT/backend/.env"
```

- 既存ファイル（通常ファイル/シンボリックリンク問わず）は無条件に削除してから張り直す。`ln: File exists` を回避する
- メイン側 `.env` 実体が存在しない場合は中止してユーザーに通知

### Phase 4: dev サーバ起動

`nohup` でバックグラウンド起動し、PID を `/tmp/sicoulab-*.pid` へ記録する。ログ出力先はプロジェクト規約（`/tmp/frontend.log`, `/tmp/backend.log`）に従う。

```bash
WT=/Users/bokuyamada/RRRRRRR777/Repositories/SicouLab/.claude/worktrees/{worktree名}

nohup make -C "$WT/frontend" dev > /tmp/frontend.log 2>&1 &
echo $! > /tmp/sicoulab-frontend.pid

nohup make -C "$WT/backend" dev > /tmp/backend.log 2>&1 &
echo $! > /tmp/sicoulab-backend.pid
```

注意:
- `cd` は使わない（プロジェクト規約）。`make` には `-C` で worktree パスを渡す
- `Bash` ツールでは `run_in_background: true` を使わず、`&` でデタッチしてから次のコマンドに進む

### Phase 5: 起動確認

5秒待ってから疎通確認:

```bash
curl -sf -o /dev/null -w "FE %{http_code}\n" http://localhost:3000 || echo "FE not ready"
curl -sf -o /dev/null -w "BE %{http_code}\n" http://localhost:8080/api/v1/health || echo "BE not ready"
```

失敗時は `/tmp/frontend.log` / `/tmp/backend.log` の末尾を `Read` して原因をユーザーに報告。

## 完了報告フォーマット

```
切替先: ticket/{番号}（{worktreeパス}）
.env: frontend/backend ともにメイン実体へリンク
FE: http://localhost:3000 ({HTTPステータス})
BE: http://localhost:8080 ({HTTPステータス})
PID: FE={pid} / BE={pid}（/tmp/sicoulab-*.pid に記録）
```

## 関連

- `frontend/.env` の `NEXT_PUBLIC_API_URL` がローカル向け（`http://localhost:8080/api/v1`）であること（CLAUDE.md 参照）
- メインリポジトリで直接 dev 起動する場合も同じ PID ファイル運用に揃えると、worktree 切替時の停止漏れがなくなる
